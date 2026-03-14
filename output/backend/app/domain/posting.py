"""Shared posting service for online bill payment and posted transactions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, ValidationError

from app.domain.accounts import AccountRecord
from app.domain.lookups import LookupError, LookupService, LookupStoreConsistencyError
from app.domain.transactions import assign_next_transaction_id
from app.domain.transactions_activity import TransactionRecord
from app.domain.transactions_reference import (
    CategoryBalanceRecord,
    TransactionCategoryRecord,
    TransactionTypeRecord,
)
from app.models import StoragePaths, StoreDocument
from app.storage import read_store, write_store


_ONLINE_PAYMENT_TYPE_CODE = "02"
_ONLINE_PAYMENT_CATEGORY_CODE = "0002"
_ONLINE_PAYMENT_SOURCE = "POS TERM"
_ONLINE_PAYMENT_DESCRIPTION = "BILL PAYMENT - ONLINE"
_ONLINE_PAYMENT_MERCHANT_ID = "999999999"
_ONLINE_PAYMENT_MERCHANT_NAME = "BILL PAYMENT"
_ONLINE_PAYMENT_MERCHANT_CITY = "N/A"
_ONLINE_PAYMENT_MERCHANT_POSTAL_CODE = "N/A"
_ZERO_AMOUNT = Decimal("0.00")


class PostingServiceError(RuntimeError):
    """Base error for payment-posting failures."""


class PostingValidationError(PostingServiceError):
    """Raised when posting inputs fail COBOL-derived validation rules."""


class PostingStoreConsistencyError(PostingServiceError):
    """Raised when persisted store data cannot support deterministic posting."""


class OnlineBillPaymentResult(BaseModel):
    """Outcome of one `COBIL00C`-style online bill payment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction: TransactionRecord
    updated_account: AccountRecord


class PostedTransactionResult(BaseModel):
    """Outcome of one `CBTRN02C`-style posted transaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction: TransactionRecord
    updated_account: AccountRecord
    updated_category_balance: CategoryBalanceRecord


@dataclass(slots=True, frozen=True)
class _StoreSnapshot:
    accounts: list[AccountRecord]
    category_balances: list[CategoryBalanceRecord]
    transactions: list[TransactionRecord]
    transaction_types: list[TransactionTypeRecord]
    transaction_categories: list[TransactionCategoryRecord]


class PostingService:
    """Storage-backed payment-posting logic derived from `COBIL00C` and `CBTRN02C`."""

    def __init__(
        self,
        paths: StoragePaths,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._paths = paths
        self._lookup_service = LookupService(paths)
        self._now_provider = now_provider or datetime.now

    def create_online_bill_payment(self, *, account_id: str) -> OnlineBillPaymentResult:
        """Append an online bill-payment transaction and zero the current balance."""
        try:
            resolved = self._lookup_service.lookup_card(account_id=account_id)
        except LookupStoreConsistencyError as error:
            raise PostingStoreConsistencyError(str(error)) from error
        except LookupError as error:
            raise PostingValidationError(str(error)) from error

        account = resolved.account
        if account.current_balance <= 0:
            raise PostingValidationError("Account has no bill payment due.")

        store = read_store(self._paths)
        snapshot = _load_snapshot(store)
        _require_online_payment_references(snapshot)

        timestamp = self._now_provider().replace(microsecond=0)
        transaction = TransactionRecord(
            transaction_id=assign_next_transaction_id(snapshot.transactions),
            transaction_type_code=_ONLINE_PAYMENT_TYPE_CODE,
            transaction_category_code=_ONLINE_PAYMENT_CATEGORY_CODE,
            source=_ONLINE_PAYMENT_SOURCE,
            description=_ONLINE_PAYMENT_DESCRIPTION,
            amount=abs(account.current_balance),
            merchant_id=_ONLINE_PAYMENT_MERCHANT_ID,
            merchant_name=_ONLINE_PAYMENT_MERCHANT_NAME,
            merchant_city=_ONLINE_PAYMENT_MERCHANT_CITY,
            merchant_postal_code=_ONLINE_PAYMENT_MERCHANT_POSTAL_CODE,
            card_number=resolved.card.card_number,
            originated_at=timestamp,
            processed_at=timestamp,
            filler=None,
        )
        updated_account = account.model_copy(update={"current_balance": _ZERO_AMOUNT})

        store["transactions"].append(transaction.model_dump(mode="python"))
        _replace_account_row(store, snapshot.accounts, updated_account)
        write_store(self._paths, store)

        return OnlineBillPaymentResult(
            transaction=transaction,
            updated_account=updated_account,
        )

    def post_transaction(self, transaction: TransactionRecord) -> PostedTransactionResult:
        """Append a posted transaction and update account and TCATBAL balances."""
        try:
            resolved = self._lookup_service.lookup_card(card_number=transaction.card_number)
        except LookupStoreConsistencyError as error:
            raise PostingStoreConsistencyError(str(error)) from error
        except LookupError as error:
            raise PostingValidationError(str(error)) from error

        account = resolved.account
        if transaction.originated_at.date() > account.expiration_date:
            raise PostingValidationError("Transaction received after account expiration.")

        store = read_store(self._paths)
        snapshot = _load_snapshot(store)
        processed_transaction = transaction
        if processed_transaction.processed_at is None:
            processed_transaction = processed_transaction.model_copy(
                update={"processed_at": self._now_provider().replace(microsecond=0)}
            )

        updated_account = _updated_account_for_posting(
            account,
            amount=processed_transaction.amount,
        )
        updated_category_balance = _updated_category_balance_for_posting(
            snapshot.category_balances,
            account_id=account.account_id,
            transaction_type_code=processed_transaction.transaction_type_code,
            transaction_category_code=processed_transaction.transaction_category_code,
            amount=processed_transaction.amount,
        )

        store["transactions"].append(processed_transaction.model_dump(mode="python"))
        _replace_account_row(store, snapshot.accounts, updated_account)
        _upsert_category_balance_row(store, snapshot.category_balances, updated_category_balance)
        write_store(self._paths, store)

        return PostedTransactionResult(
            transaction=processed_transaction,
            updated_account=updated_account,
            updated_category_balance=updated_category_balance,
        )


def _load_snapshot(store: StoreDocument) -> _StoreSnapshot:
    return _StoreSnapshot(
        accounts=_validate_collection(
            store["accounts"],
            AccountRecord,
            collection_name="accounts",
        ),
        category_balances=_validate_collection(
            store["category_balances"],
            CategoryBalanceRecord,
            collection_name="category_balances",
        ),
        transactions=_validate_collection(
            store["transactions"],
            TransactionRecord,
            collection_name="transactions",
        ),
        transaction_types=_validate_collection(
            store["transaction_types"],
            TransactionTypeRecord,
            collection_name="transaction_types",
        ),
        transaction_categories=_validate_collection(
            store["transaction_categories"],
            TransactionCategoryRecord,
            collection_name="transaction_categories",
        ),
    )


def _validate_collection[T: BaseModel](
    raw_collection: list[dict[str, object]],
    model_type: type[T],
    *,
    collection_name: str,
) -> list[T]:
    records: list[T] = []
    for index, raw_record in enumerate(raw_collection, start=1):
        try:
            records.append(model_type.model_validate(raw_record))
        except ValidationError as error:
            raise PostingStoreConsistencyError(
                f"Store {collection_name} row at index {index} is invalid: {error}"
            ) from error
    return records


def _require_online_payment_references(snapshot: _StoreSnapshot) -> None:
    if not any(
        record.transaction_type_code == _ONLINE_PAYMENT_TYPE_CODE
        for record in snapshot.transaction_types
    ):
        raise PostingStoreConsistencyError(
            "Store transaction_types is missing the online payment type code '02'."
        )
    if not any(
        record.transaction_type_code == _ONLINE_PAYMENT_TYPE_CODE
        and record.transaction_category_code == _ONLINE_PAYMENT_CATEGORY_CODE
        for record in snapshot.transaction_categories
    ):
        raise PostingStoreConsistencyError(
            "Store transaction_categories is missing the online payment category "
            "('02', '0002')."
        )


def _replace_account_row(
    store: StoreDocument,
    accounts: list[AccountRecord],
    updated_account: AccountRecord,
) -> None:
    for index, account in enumerate(accounts):
        if account.account_id == updated_account.account_id:
            store["accounts"][index] = updated_account.model_dump(mode="python")
            return
    raise PostingStoreConsistencyError(
        f"Store accounts is missing account {updated_account.account_id!r}."
    )


def _updated_account_for_posting(
    account: AccountRecord,
    *,
    amount: Decimal,
) -> AccountRecord:
    updates: dict[str, object] = {
        "current_balance": account.current_balance + amount,
    }
    if amount >= 0:
        updates["current_cycle_credit"] = account.current_cycle_credit + amount
    else:
        updates["current_cycle_debit"] = account.current_cycle_debit + amount
    return account.model_copy(update=updates)


def _updated_category_balance_for_posting(
    category_balances: list[CategoryBalanceRecord],
    *,
    account_id: str,
    transaction_type_code: str,
    transaction_category_code: str,
    amount: Decimal,
) -> CategoryBalanceRecord:
    for record in category_balances:
        if (
            record.account_id == account_id
            and record.transaction_type_code == transaction_type_code
            and record.transaction_category_code == transaction_category_code
        ):
            return record.model_copy(update={"balance": record.balance + amount})
    return CategoryBalanceRecord(
        account_id=account_id,
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        balance=amount,
        filler=None,
    )


def _upsert_category_balance_row(
    store: StoreDocument,
    category_balances: list[CategoryBalanceRecord],
    updated_category_balance: CategoryBalanceRecord,
) -> None:
    for index, record in enumerate(category_balances):
        if (
            record.account_id == updated_category_balance.account_id
            and record.transaction_type_code == updated_category_balance.transaction_type_code
            and record.transaction_category_code
            == updated_category_balance.transaction_category_code
        ):
            store["category_balances"][index] = updated_category_balance.model_dump(
                mode="python"
            )
            return
    store["category_balances"].append(updated_category_balance.model_dump(mode="python"))
