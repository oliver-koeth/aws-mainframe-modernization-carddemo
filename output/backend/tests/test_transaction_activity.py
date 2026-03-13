from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.transactions_activity import (
    REPORT_REQUEST_FIELD_COUNT,
    TRANSACTION_RECORD_WIDTH,
    JobRunDetailLevel,
    JobRunDetailRecord,
    JobRunRecord,
    JobRunStatus,
    ReportRequestType,
    TransactionActivityParseError,
    TransactionReportDetailRecord,
    parse_report_request_record,
    parse_transaction_record,
)

Parser = Callable[[str], object]


def _build_transaction_line(
    *,
    transaction_id: str,
    transaction_type_code: str,
    transaction_category_code: str,
    source: str,
    description: str,
    amount: str,
    merchant_id: str,
    merchant_name: str,
    merchant_city: str,
    merchant_postal_code: str,
    card_number: str,
    originated_at: str,
    processed_at: str = "",
    filler: str = "",
) -> str:
    return "".join(
        [
            transaction_id.ljust(16),
            transaction_type_code.ljust(2),
            transaction_category_code.ljust(4),
            source.ljust(10),
            description.ljust(100),
            amount.ljust(11),
            merchant_id.ljust(9),
            merchant_name.ljust(50),
            merchant_city.ljust(50),
            merchant_postal_code.ljust(10),
            card_number.ljust(16),
            originated_at.ljust(26),
            processed_at.ljust(26),
            filler.ljust(20),
        ],
    )


def test_parse_transaction_record_from_seed_line() -> None:
    record = parse_transaction_record(
        "0000000000683580010001POS TERM  Purchase at Abshire-Lowe"
        "                                                                            "
        "0000005047G800000000Abshire-Lowe                                      "
        "North Enoshaven                                   72112     4859452612877065"
        "2022-06-10 19:27:53.000000                          ",
    )

    assert record.transaction_id == "0000000000683580"
    assert record.transaction_type_code == "01"
    assert record.transaction_category_code == "0001"
    assert record.source == "POS TERM"
    assert record.description == "Purchase at Abshire-Lowe"
    assert record.amount == Decimal("504.77")
    assert record.merchant_id == "800000000"
    assert record.merchant_name == "Abshire-Lowe"
    assert record.merchant_city == "North Enoshaven"
    assert record.merchant_postal_code == "72112"
    assert record.card_number == "4859452612877065"
    assert record.originated_at == datetime(2022, 6, 10, 19, 27, 53)
    assert record.processed_at is None
    assert record.filler is None


def test_parse_transaction_record_supports_negative_signed_amounts_and_processed_timestamp() -> None:
    line = _build_transaction_line(
        transaction_id="TXN-000000000001",
        transaction_type_code="02",
        transaction_category_code="0002",
        source="OPERATOR",
        description="Return item",
        amount="0000000012R",
        merchant_id="999999999",
        merchant_name="BILL PAYMENT",
        merchant_city="N/A",
        merchant_postal_code="N/A",
        card_number="1234567890123456",
        originated_at="2026-03-10 12:30:45.123456",
        processed_at="2026-03-10 12:31:00.000000",
    )

    record = parse_transaction_record(line)

    assert len(line) == TRANSACTION_RECORD_WIDTH
    assert record.amount == Decimal("-1.29")
    assert record.processed_at == datetime(2026, 3, 10, 12, 31, 0)


def test_parse_report_request_record_from_runtime_line() -> None:
    record = parse_report_request_record("2026-03-10 16:50:02|USER0001|Custom|2026-03-01|2026-03-10")

    assert record.requested_at == datetime(2026, 3, 10, 16, 50, 2)
    assert record.requested_by_user_id == "USER0001"
    assert record.report_type is ReportRequestType.CUSTOM
    assert record.start_date == date(2026, 3, 1)
    assert record.end_date == date(2026, 3, 10)


@pytest.mark.parametrize(
    ("parser", "line", "expected_message"),
    [
        (
            parse_transaction_record,
            _build_transaction_line(
                transaction_id="TXN-000000000001",
                transaction_type_code="01",
                transaction_category_code="00A1",
                source="POS TERM",
                description="Purchase",
                amount="0000000100{",
                merchant_id="800000000",
                merchant_name="Shop",
                merchant_city="City",
                merchant_postal_code="12345",
                card_number="1234567890123456",
                originated_at="2026-03-10 12:30:45.123456",
            ),
            "Line 1: TRAN-CAT-CD must contain only digits, received '00A1'.",
        ),
        (
            parse_transaction_record,
            _build_transaction_line(
                transaction_id="TXN-000000000001",
                transaction_type_code="01",
                transaction_category_code="0001",
                source="POS TERM",
                description="Purchase",
                amount="0000000100X",
                merchant_id="800000000",
                merchant_name="Shop",
                merchant_city="City",
                merchant_postal_code="12345",
                card_number="1234567890123456",
                originated_at="2026-03-10 12:30:45.123456",
            ),
            "Line 1: TRAN-AMT has unsupported signed-digit suffix 'X' in '0000000100X'.",
        ),
        (
            parse_transaction_record,
            _build_transaction_line(
                transaction_id="TXN-000000000001",
                transaction_type_code="01",
                transaction_category_code="0001",
                source="POS TERM",
                description="Purchase",
                amount="0000000100{",
                merchant_id="80000000A",
                merchant_name="Shop",
                merchant_city="City",
                merchant_postal_code="12345",
                card_number="1234567890123456",
                originated_at="2026-03-10 12:30:45.123456",
            ),
            "Line 1: TRAN-MERCHANT-ID must contain only digits, received '80000000A'.",
        ),
        (
            parse_transaction_record,
            _build_transaction_line(
                transaction_id="TXN-000000000001",
                transaction_type_code="01",
                transaction_category_code="0001",
                source="POS TERM",
                description="Purchase",
                amount="0000000100{",
                merchant_id="800000000",
                merchant_name="Shop",
                merchant_city="City",
                merchant_postal_code="12345",
                card_number="1234567890123456",
                originated_at="2026/03/10 12:30:45",
            ),
            "Line 1: TRAN-ORIG-TS must be ISO timestamp text, received '2026/03/10 12:30:45'.",
        ),
        (
            parse_report_request_record,
            "2026-03-10 16:50:02|USER0001|Weekly|2026-03-01|2026-03-10",
            "Line 1: unsupported REQUEST-REPORT-NAME 'Weekly'; expected one of Monthly, Yearly, Custom.",
        ),
        (
            parse_report_request_record,
            "2026-03-10 16:50:02|USER0001|Custom|2026-03-11|2026-03-10",
            "Line 1: REQUEST-START-DATE must not be after REQUEST-END-DATE.",
        ),
        (
            parse_report_request_record,
            "2026-03-10|USER0001|Custom|2026-03-01|2026-03-10",
            "Line 1: REQUEST-TIMESTAMP must be YYYY-MM-DD HH:MM:SS, received '2026-03-10'.",
        ),
        (
            parse_report_request_record,
            "2026-03-10 16:50:02|USER0001|Custom|2026-03-01",
            "Line 1: expected 5 pipe-delimited fields, received 4.",
        ),
    ],
)
def test_transaction_activity_parsers_reject_malformed_lines(
    parser: Parser,
    line: str,
    expected_message: str,
) -> None:
    with pytest.raises(TransactionActivityParseError, match=expected_message):
        parser(line)


def test_transaction_activity_json_serialization_contract() -> None:
    report_detail = TransactionReportDetailRecord(
        transaction_id="TXN-000000000001",
        account_id="00000000001",
        transaction_type_code="01",
        transaction_type_description="Purchase",
        transaction_category_code="0001",
        transaction_category_description="Regular Sales Draft",
        source="POS TERM",
        amount=Decimal("12.34"),
    )
    job_run = JobRunRecord(
        job_run_id="daily-report-20260310-1",
        job_name="daily-report",
        status=JobRunStatus.SUCCEEDED,
        queued_at=datetime(2026, 3, 10, 16, 50, 2),
        started_at=datetime(2026, 3, 10, 16, 50, 3),
        completed_at=datetime(2026, 3, 10, 16, 50, 4),
    )
    job_run_detail = JobRunDetailRecord(
        job_run_id="daily-report-20260310-1",
        sequence_number=1,
        recorded_at=datetime(2026, 3, 10, 16, 50, 4),
        level=JobRunDetailLevel.INFO,
        message="Generated daily report",
        context={"report_type": "Custom"},
    )

    assert report_detail.model_dump(mode="json") == {
        "transaction_id": "TXN-000000000001",
        "account_id": "00000000001",
        "transaction_type_code": "01",
        "transaction_type_description": "Purchase",
        "transaction_category_code": "0001",
        "transaction_category_description": "Regular Sales Draft",
        "source": "POS TERM",
        "amount": "12.34",
    }
    assert job_run.model_dump(mode="json") == {
        "job_run_id": "daily-report-20260310-1",
        "job_name": "daily-report",
        "status": "succeeded",
        "queued_at": "2026-03-10T16:50:02",
        "started_at": "2026-03-10T16:50:03",
        "completed_at": "2026-03-10T16:50:04",
        "error_message": None,
    }
    assert job_run_detail.model_dump(mode="json") == {
        "job_run_id": "daily-report-20260310-1",
        "sequence_number": 1,
        "recorded_at": "2026-03-10T16:50:04",
        "level": "info",
        "message": "Generated daily report",
        "context": {"report_type": "Custom"},
    }


def test_report_request_record_field_count_constant_matches_runtime_format() -> None:
    assert REPORT_REQUEST_FIELD_COUNT == 5
