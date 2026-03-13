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
from app.domain.posting import (
    PostingService,
    PostingStoreConsistencyError,
    PostingValidationError,
)
from app.domain.transactions_activity import TransactionRecord
from app.domain.transactions_reference import (
    CategoryBalanceRecord,
    TransactionCategoryRecord,
    TransactionTypeRecord,
)
from app.models import StoragePaths, default_store_document
from app.storage import read_store, write_store


def test_create_online_bill_payment_appends_transaction_and_zeroes_balance(
    tmp_path,
) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )
    service = PostingService(
        paths,
        now_provider=lambda: datetime(2026, 3, 13, 14, 5, 6, 789123),
    )
    payload = _build_store(current_balance=Decimal("194.00"))
    payload["category_balances"] = [
        CategoryBalanceRecord(
            account_id="00000000001",
            transaction_type_code="01",
            transaction_category_code="0001",
            balance=Decimal("80.00"),
            filler=None,
        ).model_dump(mode="python")
    ]
    write_store(paths, payload)

    result = service.create_online_bill_payment(account_id="00000000001")

    assert result.transaction.transaction_id == "0000000000000002"
    assert result.transaction.transaction_type_code == "02"
    assert result.transaction.transaction_category_code == "0002"
    assert result.transaction.amount == Decimal("194.00")
    assert result.transaction.source == "POS TERM"
    assert result.transaction.description == "BILL PAYMENT - ONLINE"
    assert result.transaction.merchant_id == "999999999"
    assert result.transaction.card_number == "4111111111111111"
    assert result.transaction.originated_at == datetime(2026, 3, 13, 14, 5, 6)
    assert result.transaction.processed_at == datetime(2026, 3, 13, 14, 5, 6)
    assert result.updated_account.current_balance == Decimal("0.00")
    assert result.updated_account.current_cycle_credit == Decimal("15.00")
    assert result.updated_account.current_cycle_debit == Decimal("209.00")

    persisted_store = read_store(paths)
    persisted_account = AccountRecord.model_validate(persisted_store["accounts"][0])
    persisted_transaction = TransactionRecord.model_validate(
        persisted_store["transactions"][-1]
    )
    persisted_category_balance = CategoryBalanceRecord.model_validate(
        persisted_store["category_balances"][0]
    )

    assert persisted_account.current_balance == Decimal("0.00")
    assert persisted_transaction == result.transaction
    assert persisted_category_balance.balance == Decimal("80.00")


def test_post_transaction_updates_account_cycle_fields_and_category_balance(
    tmp_path,
) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )
    service = PostingService(
        paths,
        now_provider=lambda: datetime(2026, 3, 14, 9, 30, 45, 123456),
    )
    payload = _build_store(
        current_balance=Decimal("194.00"),
        current_cycle_credit=Decimal("15.00"),
        current_cycle_debit=Decimal("209.00"),
    )
    write_store(paths, payload)

    result = service.post_transaction(
        TransactionRecord(
            transaction_id="0000000000000099",
            transaction_type_code="02",
            transaction_category_code="0002",
            source="BATCHJOB",
            description="Nightly payment posting",
            amount=Decimal("-50.00"),
            merchant_id="999999999",
            merchant_name="BILL PAYMENT",
            merchant_city="N/A",
            merchant_postal_code="N/A",
            card_number="4111111111111111",
            originated_at=datetime(2026, 3, 13, 16, 0, 0),
            processed_at=None,
            filler=None,
        )
    )

    assert result.transaction.processed_at == datetime(2026, 3, 14, 9, 30, 45)
    assert result.updated_account.current_balance == Decimal("144.00")
    assert result.updated_account.current_cycle_credit == Decimal("15.00")
    assert result.updated_account.current_cycle_debit == Decimal("159.00")
    assert result.updated_category_balance.balance == Decimal("-50.00")

    persisted_store = read_store(paths)
    persisted_account = AccountRecord.model_validate(persisted_store["accounts"][0])
    persisted_category_balance = CategoryBalanceRecord.model_validate(
        persisted_store["category_balances"][0]
    )
    persisted_transaction = TransactionRecord.model_validate(
        persisted_store["transactions"][-1]
    )

    assert persisted_account.current_balance == Decimal("144.00")
    assert persisted_category_balance.transaction_type_code == "02"
    assert persisted_category_balance.transaction_category_code == "0002"
    assert persisted_category_balance.balance == Decimal("-50.00")
    assert persisted_transaction == result.transaction


def test_create_online_bill_payment_rejects_non_positive_balance(tmp_path) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )
    service = PostingService(paths)
    payload = _build_store(current_balance=Decimal("0.00"))
    write_store(paths, payload)

    with pytest.raises(
        PostingValidationError,
        match="Account has no bill payment due.",
    ):
        service.create_online_bill_payment(account_id="00000000001")


def test_post_transaction_surfaces_invalid_persisted_rows(tmp_path) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )
    service = PostingService(paths)
    payload = _build_store()
    payload["category_balances"] = [{"account_id": "broken"}]
    write_store(paths, payload)

    with pytest.raises(
        PostingStoreConsistencyError,
        match="Store category_balances row at index 1 is invalid:",
    ):
        service.post_transaction(_posted_payment_transaction())


def _posted_payment_transaction() -> TransactionRecord:
    return TransactionRecord(
        transaction_id="0000000000000099",
        transaction_type_code="02",
        transaction_category_code="0002",
        source="BATCHJOB",
        description="Nightly payment posting",
        amount=Decimal("-50.00"),
        merchant_id="999999999",
        merchant_name="BILL PAYMENT",
        merchant_city="N/A",
        merchant_postal_code="N/A",
        card_number="4111111111111111",
        originated_at=datetime(2026, 3, 13, 16, 0, 0),
        processed_at=None,
        filler=None,
    )


def _build_store(
    *,
    current_balance: Decimal = Decimal("194.00"),
    current_cycle_credit: Decimal = Decimal("15.00"),
    current_cycle_debit: Decimal = Decimal("209.00"),
) -> dict[str, object]:
    payload = default_store_document()
    payload["accounts"] = [
        AccountRecord(
            account_id="00000000001",
            active_status=AccountActiveStatus.ACTIVE,
            is_active=True,
            current_balance=current_balance,
            credit_limit=Decimal("2500.00"),
            cash_credit_limit=Decimal("500.00"),
            open_date=date(2024, 1, 1),
            expiration_date=date(2028, 1, 1),
            reissue_date=date(2026, 1, 1),
            current_cycle_credit=current_cycle_credit,
            current_cycle_debit=current_cycle_debit,
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
            expiration_date=date(2028, 1, 1),
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
            description="Electronic payment",
            filler="0000",
        ).model_dump(mode="python"),
    ]
    payload["transactions"] = [
        TransactionRecord(
            transaction_id="0000000000000001",
            transaction_type_code="01",
            transaction_category_code="0001",
            source="POS TERM",
            description="Existing purchase",
            amount=Decimal("20.00"),
            merchant_id="800000000",
            merchant_name="Existing Shop",
            merchant_city="Boston",
            merchant_postal_code="02110",
            card_number="4111111111111111",
            originated_at=datetime(2026, 3, 10, 9, 15, 0),
            processed_at=datetime(2026, 3, 10, 9, 15, 0),
            filler=None,
        ).model_dump(mode="python")
    ]
    return payload
