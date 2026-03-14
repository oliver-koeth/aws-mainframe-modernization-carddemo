from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.accounts import (
    AccountActiveStatus,
    AccountRecord,
    CardAccountXrefRecord,
    CardActiveStatus,
    CardRecord,
)
from app.domain.transactions import (
    TransactionCreateRequest,
    TransactionService,
    TransactionStoreConsistencyError,
    TransactionValidationError,
)
from app.domain.transactions_activity import TransactionRecord
from app.domain.transactions_reference import (
    CategoryBalanceRecord,
    TransactionCategoryRecord,
    TransactionTypeRecord,
)
from app.models import default_store_document
from app.services import build_backend_state, build_transaction_service
from app.storage import read_store, write_store


def test_create_transaction_appends_normalized_record_with_next_numeric_id(
    tmp_path,
) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = _build_transaction_store()
    payload["transactions"] = [
        TransactionRecord(
            transaction_id="0000000000000007",
            transaction_type_code="01",
            transaction_category_code="0001",
            source="POS TERM",
            description="Existing purchase",
            amount=Decimal("10.00"),
            merchant_id="800000000",
            merchant_name="Existing Shop",
            merchant_city="Boston",
            merchant_postal_code="02110",
            card_number="4111111111111111",
            originated_at=datetime(2026, 3, 10, 9, 15, 0),
            processed_at=datetime(2026, 3, 10, 9, 15, 0),
            filler=None,
        ).model_dump(mode="python"),
        TransactionRecord(
            transaction_id="NOTNUMERIC000001",
            transaction_type_code="01",
            transaction_category_code="0001",
            source="POS TERM",
            description="Ignored for next-id scan",
            amount=Decimal("11.00"),
            merchant_id="800000000",
            merchant_name="Existing Shop",
            merchant_city="Boston",
            merchant_postal_code="02110",
            card_number="4111111111111111",
            originated_at=datetime(2026, 3, 11, 9, 15, 0),
            processed_at=datetime(2026, 3, 11, 9, 15, 0),
            filler=None,
        ).model_dump(mode="python"),
    ]
    write_store(backend_state.paths, payload)

    service = build_transaction_service(backend_state)
    result = service.create_transaction(
        TransactionCreateRequest(
            account_id="00000000001",
            transaction_type_code="01",
            transaction_category_code="0001",
            source=" POS TERM ",
            amount="+00000123.45",
            description=" Purchase at Corner Shop ",
            originated_on="2026-03-12",
            merchant_id="800000001",
            merchant_name=" Corner Shop ",
            merchant_city=" New York ",
            merchant_postal_code=" 10001 ",
        )
    )

    assert result.transaction.transaction_id == "0000000000000008"
    assert result.transaction.amount == Decimal("123.45")
    assert result.transaction.card_number == "4111111111111111"
    assert result.transaction.originated_at == datetime(2026, 3, 12, 0, 0, 0)
    assert result.transaction.processed_at == datetime(2026, 3, 12, 0, 0, 0)
    assert result.transaction_type.description == "Purchase"
    assert result.transaction_category.description == "Regular Sales Draft"
    assert result.category_balance.account_id == "00000000001"

    persisted_store = read_store(backend_state.paths)
    persisted_transaction = TransactionRecord.model_validate(
        persisted_store["transactions"][-1]
    )
    assert persisted_transaction == result.transaction


def test_validate_transaction_rejects_invalid_inputs_and_missing_references(
    tmp_path,
) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = _build_transaction_store()
    write_store(backend_state.paths, payload)
    service = build_transaction_service(backend_state)

    with pytest.raises(
        TransactionValidationError,
        match="Type code must be a 2-digit numeric value.",
    ):
        service.validate_transaction(
            _request(transaction_type_code="A1")
        )

    with pytest.raises(
        TransactionValidationError,
        match="Transaction category code '9999' was not found for type '01'.",
    ):
        service.validate_transaction(
            _request(transaction_category_code="9999")
        )

    with pytest.raises(
        TransactionValidationError,
        match=(
            "Account '00000000001' does not have a category balance for type '02' "
            "and category '0002'."
        ),
    ):
        service.validate_transaction(
            _request(transaction_type_code="02", transaction_category_code="0002")
        )

    with pytest.raises(
        TransactionValidationError,
        match="Amount must start with \\+ or -.",
    ):
        service.validate_transaction(
            _request(amount="12.34")
        )

    with pytest.raises(
        TransactionValidationError,
        match="Original date should be in format YYYY-MM-DD.",
    ):
        service.validate_transaction(
            _request(originated_on="2026-02-30")
        )

    with pytest.raises(
        TransactionValidationError,
        match="Merchant ID must be numeric.",
    ):
        service.validate_transaction(
            _request(merchant_id="80000ABCD")
        )


def test_validate_transaction_rejects_expired_account_activity(tmp_path) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = _build_transaction_store(expiration_date=date(2026, 3, 1))
    write_store(backend_state.paths, payload)
    service = build_transaction_service(backend_state)

    with pytest.raises(
        TransactionValidationError,
        match="Transaction received after account expiration.",
    ):
        service.validate_transaction(
            _request(originated_on="2026-03-12")
        )


def test_create_transaction_surfaces_store_consistency_errors(tmp_path) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = _build_transaction_store()
    payload["transactions"] = [{"transaction_id": "broken"}]
    write_store(backend_state.paths, payload)
    service = TransactionService(backend_state.paths)

    with pytest.raises(
        TransactionStoreConsistencyError,
        match="Store transactions row at index 1 is invalid:",
    ):
        service.create_transaction(_request())


def _request(**overrides: object) -> TransactionCreateRequest:
    values: dict[str, object] = {
        "account_id": "00000000001",
        "transaction_type_code": "01",
        "transaction_category_code": "0001",
        "source": "POS TERM",
        "amount": "+00000123.45",
        "description": "Purchase at Corner Shop",
        "originated_on": "2026-03-12",
        "merchant_id": "800000001",
        "merchant_name": "Corner Shop",
        "merchant_city": "New York",
        "merchant_postal_code": "10001",
    }
    values.update(overrides)
    return TransactionCreateRequest.model_validate(values)


def _build_transaction_store(
    *,
    expiration_date: date = date(2028, 1, 1),
) -> dict[str, object]:
    payload = default_store_document()
    payload["accounts"] = [
        AccountRecord(
            account_id="00000000001",
            active_status=AccountActiveStatus.ACTIVE,
            is_active=True,
            current_balance=Decimal("100.00"),
            credit_limit=Decimal("2500.00"),
            cash_credit_limit=Decimal("500.00"),
            open_date=date(2024, 1, 1),
            expiration_date=expiration_date,
            reissue_date=date(2026, 1, 1),
            current_cycle_credit=Decimal("0.00"),
            current_cycle_debit=Decimal("0.00"),
            billing_postal_code="10001",
            group_id="VIPGROUP",
            filler=None,
        ).model_dump(mode="python")
    ]
    payload["cards"] = [
        CardRecord(
            card_number="4111111111111111",
            account_id="00000000001",
            cvv_code="123",
            embossed_name="Ada Lovelace",
            expiration_date=expiration_date,
            active_status=CardActiveStatus.ACTIVE,
            is_active=True,
            filler=None,
        ).model_dump(mode="python")
    ]
    payload["card_account_xref"] = [
        CardAccountXrefRecord(
            card_number="4111111111111111",
            customer_id="000000001",
            account_id="00000000001",
            filler=None,
        ).model_dump(mode="python")
    ]
    payload["transaction_types"] = [
        TransactionTypeRecord(
            transaction_type_code="01",
            description="Purchase",
            filler="00000000",
        ).model_dump(mode="python"),
        TransactionTypeRecord(
            transaction_type_code="02",
            description="Payment",
            filler="00000000",
        ).model_dump(mode="python"),
    ]
    payload["transaction_categories"] = [
        TransactionCategoryRecord(
            transaction_type_code="01",
            transaction_category_code="0001",
            description="Regular Sales Draft",
            filler="0000",
        ).model_dump(mode="python"),
        TransactionCategoryRecord(
            transaction_type_code="02",
            transaction_category_code="0002",
            description="Regular Payment",
            filler="0000",
        ).model_dump(mode="python"),
    ]
    payload["category_balances"] = [
        CategoryBalanceRecord(
            account_id="00000000001",
            transaction_type_code="01",
            transaction_category_code="0001",
            balance=Decimal("0.00"),
            filler="0" * 22,
        ).model_dump(mode="python")
    ]
    return payload
