from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.report_requests import (
    ReportRequestCreateRequest,
    ReportRequestService,
    ReportRequestStoreConsistencyError,
    ReportRequestValidationError,
)
from app.domain.transactions_activity import ReportRequestRecord, ReportRequestType
from app.domain.users import UserName, UserRole, UserSecurityRecord
from app.models import default_store_document
from app.storage import write_store


def test_create_report_request_appends_custom_request_and_lists_in_store_order(
    storage_paths,
) -> None:
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="USER0001",
            name=UserName(first_name="CARD", last_name="USER"),
            password="PASSWORD",
            role=UserRole.USER,
            user_type_code="U",
        ).model_dump(mode="python")
    ]
    payload["report_requests"] = [
        ReportRequestRecord(
            requested_at=datetime(2026, 3, 10, 16, 50, 2),
            requested_by_user_id="USER0001",
            report_type=ReportRequestType.CUSTOM,
            start_date=datetime(2026, 3, 1).date(),
            end_date=datetime(2026, 3, 10).date(),
        ).model_dump(mode="python")
    ]
    write_store(storage_paths, payload)

    service = ReportRequestService(
        storage_paths,
        now_provider=lambda: datetime(2026, 3, 13, 9, 15, 1),
    )

    created = service.create_report_request(
        ReportRequestCreateRequest(
            requested_by_user_id="user0001",
            report_type="Custom",
            start_date="2026-03-11",
            end_date="2026-03-13",
        )
    )
    requests = service.list_report_requests(requested_by_user_id="USER0001")

    assert created.requested_at == datetime(2026, 3, 13, 9, 15, 1)
    assert created.requested_by_user_id == "USER0001"
    assert created.report_type is ReportRequestType.CUSTOM
    assert created.start_date.isoformat() == "2026-03-11"
    assert created.end_date.isoformat() == "2026-03-13"
    assert [request.start_date.isoformat() for request in requests] == [
        "2026-03-01",
        "2026-03-11",
    ]


def test_create_report_request_derives_monthly_and_yearly_ranges(storage_paths) -> None:
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="ADMIN001",
            name=UserName(first_name="ADMIN", last_name="USER"),
            password="PASSWORD",
            role=UserRole.ADMIN,
            user_type_code="A",
        ).model_dump(mode="python")
    ]
    write_store(storage_paths, payload)

    service = ReportRequestService(
        storage_paths,
        now_provider=lambda: datetime(2026, 2, 14, 8, 0, 0),
    )

    monthly = service.create_report_request(
        ReportRequestCreateRequest(
            requested_by_user_id="ADMIN001",
            report_type="monthly",
        )
    )
    yearly = service.create_report_request(
        ReportRequestCreateRequest(
            requested_by_user_id="ADMIN001",
            report_type="Yearly",
        )
    )

    assert monthly.start_date.isoformat() == "2026-02-01"
    assert monthly.end_date.isoformat() == "2026-02-28"
    assert yearly.start_date.isoformat() == "2026-01-01"
    assert yearly.end_date.isoformat() == "2026-12-31"


@pytest.mark.parametrize(
    ("create_request", "expected_message"),
    [
        (
            ReportRequestCreateRequest(
                requested_by_user_id="UNKNOWN1",
                report_type="Custom",
                start_date="2026-03-01",
                end_date="2026-03-10",
            ),
            "User ID 'UNKNOWN1' was not found.",
        ),
        (
            ReportRequestCreateRequest(
                requested_by_user_id="USER0001",
                report_type="Weekly",
                start_date="2026-03-01",
                end_date="2026-03-10",
            ),
            "Report type must be one of: Monthly, Yearly, Custom.",
        ),
        (
            ReportRequestCreateRequest(
                requested_by_user_id="USER0001",
                report_type="Custom",
                start_date="2026-03-11",
                end_date="2026-03-10",
            ),
            "Start date must not be after end date.",
        ),
        (
            ReportRequestCreateRequest(
                requested_by_user_id="USER0001",
                report_type="Monthly",
                start_date="2026-03-01",
            ),
            "Start and end dates are only accepted for Custom reports.",
        ),
    ],
)
def test_report_request_service_rejects_invalid_create_inputs(
    storage_paths,
    create_request: ReportRequestCreateRequest,
    expected_message: str,
) -> None:
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="USER0001",
            name=UserName(first_name="CARD", last_name="USER"),
            password="PASSWORD",
            role=UserRole.USER,
            user_type_code="U",
        ).model_dump(mode="python")
    ]
    write_store(storage_paths, payload)

    service = ReportRequestService(storage_paths)

    with pytest.raises(ReportRequestValidationError, match=expected_message):
        service.create_report_request(create_request)


def test_list_report_requests_rejects_invalid_or_dangling_store_rows(storage_paths) -> None:
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="USER0001",
            name=UserName(first_name="CARD", last_name="USER"),
            password="PASSWORD",
            role=UserRole.USER,
            user_type_code="U",
        ).model_dump(mode="python")
    ]
    payload["report_requests"] = [
        {
            "requested_at": datetime(2026, 3, 10, 16, 50, 2),
            "requested_by_user_id": "UNKNOWN1",
            "report_type": "Custom",
            "start_date": datetime(2026, 3, 1).date(),
            "end_date": datetime(2026, 3, 10).date(),
        }
    ]
    write_store(storage_paths, payload)

    service = ReportRequestService(storage_paths)

    with pytest.raises(
        ReportRequestStoreConsistencyError,
        match="Store report_requests row at index 1 references unknown user ID 'UNKNOWN1'.",
    ):
        service.list_report_requests()
