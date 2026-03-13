"""Transaction validation and creation service derived from `COTRN02C`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.accounts import AccountRecord, CardRecord
from app.domain.lookups import (
    LookupError,
    LookupService,
    LookupStoreConsistencyError,
)
from app.domain.transactions_activity import TransactionRecord
from app.domain.transactions_reference import (
    CategoryBalanceRecord,
    TransactionCategoryRecord,
    TransactionTypeRecord,
)
from app.models import StoragePaths
from app.storage import read_store, write_store


_TYPE_CODE_PATTERN = re.compile(r"^\d{2}$")
_CATEGORY_CODE_PATTERN = re.compile(r"^\d{4}$")
_MERCHANT_ID_PATTERN = re.compile(r"^\d{9}$")
_AMOUNT_PATTERN = re.compile(r"^[+-]\d{1,8}\.\d{2}$")


class TransactionServiceError(RuntimeError):
    """Base error for transaction validation and creation failures."""


class TransactionValidationError(TransactionServiceError):
    """Raised when transaction input does not satisfy `COTRN02C` semantics."""


class TransactionStoreConsistencyError(TransactionServiceError):
    """Raised when persisted transaction state cannot be resolved deterministically."""


class TransactionCreateRequest(BaseModel):
    """Raw transaction-add inputs modeled on the `COTRN02C` prompts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str | None = None
    card_number: str | None = None
    transaction_type_code: str
    transaction_category_code: str
    source: str
    amount: str
    description: str
    originated_on: str
    processed_on: str | None = None
    merchant_id: str
    merchant_name: str
    merchant_city: str
    merchant_postal_code: str


class ValidatedTransactionInput(BaseModel):
    """Normalized transaction input after shared validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account: AccountRecord
    card: CardRecord
    transaction_type: TransactionTypeRecord
    transaction_category: TransactionCategoryRecord
    category_balance: CategoryBalanceRecord
    source: str = Field(min_length=1, max_length=10)
    description: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(decimal_places=2)
    merchant_id: str = Field(min_length=9, max_length=9, pattern=r"^\d{9}$")
    merchant_name: str = Field(min_length=1, max_length=50)
    merchant_city: str = Field(min_length=1, max_length=50)
    merchant_postal_code: str = Field(min_length=1, max_length=10)
    originated_on: date
    processed_on: date


class CreatedTransaction(BaseModel):
    """Persisted transaction plus the reference records resolved during creation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction: TransactionRecord
    account: AccountRecord
    card: CardRecord
    transaction_type: TransactionTypeRecord
    transaction_category: TransactionCategoryRecord
    category_balance: CategoryBalanceRecord


@dataclass(slots=True, frozen=True)
class _ReferenceSnapshot:
    transaction_types: dict[str, TransactionTypeRecord]
    transaction_categories: dict[tuple[str, str], TransactionCategoryRecord]
    category_balances: dict[tuple[str, str, str], CategoryBalanceRecord]
    transactions: list[TransactionRecord]


class TransactionService:
    """Storage-backed transaction validation and append behavior for Phase 1."""

    def __init__(self, paths: StoragePaths) -> None:
        self._paths = paths
        self._lookup_service = LookupService(paths)

    def validate_transaction(
        self,
        request: TransactionCreateRequest,
    ) -> ValidatedTransactionInput:
        """Validate and normalize one `COTRN02C`-style transaction request."""
        account, card = self._resolve_account_and_card(request)
        references = self._load_reference_snapshot()

        transaction_type_code = _require_code(
            request.transaction_type_code,
            pattern=_TYPE_CODE_PATTERN,
            message="Type code must be a 2-digit numeric value.",
        )
        transaction_category_code = _require_code(
            request.transaction_category_code,
            pattern=_CATEGORY_CODE_PATTERN,
            message="Category code must be a 4-digit numeric value.",
        )
        transaction_type = references.transaction_types.get(transaction_type_code)
        if transaction_type is None:
            raise TransactionValidationError(
                f"Transaction type code {transaction_type_code!r} was not found."
            )

        category_key = (transaction_type_code, transaction_category_code)
        transaction_category = references.transaction_categories.get(category_key)
        if transaction_category is None:
            raise TransactionValidationError(
                "Transaction category code "
                f"{transaction_category_code!r} was not found for type "
                f"{transaction_type_code!r}."
            )

        category_balance = references.category_balances.get(
            (account.account_id, transaction_type_code, transaction_category_code)
        )
        if category_balance is None:
            raise TransactionValidationError(
                "Account "
                f"{account.account_id!r} does not have a category balance for "
                f"type {transaction_type_code!r} and category "
                f"{transaction_category_code!r}."
            )

        source = _require_text(
            request.source,
            blank_message="Source cannot be empty.",
            too_long_message="Source must be 10 characters or fewer.",
            max_length=10,
        )
        description = _require_text(
            request.description,
            blank_message="Description cannot be empty.",
            too_long_message="Description must be 100 characters or fewer.",
            max_length=100,
        )
        amount = _parse_amount(request.amount)
        originated_on = _parse_entry_date(
            request.originated_on,
            invalid_message="Original date should be in format YYYY-MM-DD.",
        )
        processed_on = (
            originated_on
            if request.processed_on is None or request.processed_on.strip() == ""
            else _parse_entry_date(
                request.processed_on,
                invalid_message="Processed date should be in format YYYY-MM-DD.",
            )
        )
        merchant_id = _require_code(
            request.merchant_id,
            pattern=_MERCHANT_ID_PATTERN,
            message="Merchant ID must be numeric.",
        )
        merchant_name = _require_text(
            request.merchant_name,
            blank_message="Merchant name cannot be empty.",
            too_long_message="Merchant name must be 50 characters or fewer.",
            max_length=50,
        )
        merchant_city = _require_text(
            request.merchant_city,
            blank_message="Merchant city cannot be empty.",
            too_long_message="Merchant city must be 50 characters or fewer.",
            max_length=50,
        )
        merchant_postal_code = _require_text(
            request.merchant_postal_code,
            blank_message="Merchant ZIP cannot be empty.",
            too_long_message="Merchant ZIP must be 10 characters or fewer.",
            max_length=10,
        )
        if originated_on > account.expiration_date:
            raise TransactionValidationError(
                "Transaction received after account expiration."
            )

        return ValidatedTransactionInput(
            account=account,
            card=card,
            transaction_type=transaction_type,
            transaction_category=transaction_category,
            category_balance=category_balance,
            source=source,
            description=description,
            amount=amount,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            merchant_city=merchant_city,
            merchant_postal_code=merchant_postal_code,
            originated_on=originated_on,
            processed_on=processed_on,
        )

    def create_transaction(
        self,
        request: TransactionCreateRequest,
    ) -> CreatedTransaction:
        """Persist one validated transaction by appending it to `transactions[]`."""
        validated = self.validate_transaction(request)
        store = read_store(self._paths)
        existing_transactions = _validate_collection(
            store["transactions"],
            TransactionRecord,
            collection_name="transactions",
        )
        next_transaction_id = _assign_next_transaction_id(existing_transactions)
        transaction = TransactionRecord(
            transaction_id=next_transaction_id,
            transaction_type_code=validated.transaction_type.transaction_type_code,
            transaction_category_code=validated.transaction_category.transaction_category_code,
            source=validated.source,
            description=validated.description,
            amount=validated.amount,
            merchant_id=validated.merchant_id,
            merchant_name=validated.merchant_name,
            merchant_city=validated.merchant_city,
            merchant_postal_code=validated.merchant_postal_code,
            card_number=validated.card.card_number,
            originated_at=datetime.combine(validated.originated_on, time.min),
            processed_at=datetime.combine(validated.processed_on, time.min),
            filler=None,
        )
        store["transactions"].append(transaction.model_dump(mode="python"))
        write_store(self._paths, store)

        return CreatedTransaction(
            transaction=transaction,
            account=validated.account,
            card=validated.card,
            transaction_type=validated.transaction_type,
            transaction_category=validated.transaction_category,
            category_balance=validated.category_balance,
        )

    def _resolve_account_and_card(
        self,
        request: TransactionCreateRequest,
    ) -> tuple[AccountRecord, CardRecord]:
        try:
            lookup_result = self._lookup_service.lookup_card(
                account_id=request.account_id,
                card_number=request.card_number,
            )
        except LookupStoreConsistencyError as error:
            raise TransactionStoreConsistencyError(str(error)) from error
        except LookupError as error:
            raise TransactionValidationError(str(error)) from error

        return lookup_result.account, lookup_result.card

    def _load_reference_snapshot(self) -> _ReferenceSnapshot:
        store = read_store(self._paths)
        transaction_types = _validate_collection(
            store["transaction_types"],
            TransactionTypeRecord,
            collection_name="transaction_types",
        )
        transaction_categories = _validate_collection(
            store["transaction_categories"],
            TransactionCategoryRecord,
            collection_name="transaction_categories",
        )
        category_balances = _validate_collection(
            store["category_balances"],
            CategoryBalanceRecord,
            collection_name="category_balances",
        )
        transactions = _validate_collection(
            store["transactions"],
            TransactionRecord,
            collection_name="transactions",
        )
        return _ReferenceSnapshot(
            transaction_types=_build_unique_index(
                transaction_types,
                key_name="transaction_type_code",
                collection_name="transaction_types",
            ),
            transaction_categories=_build_composite_index(
                transaction_categories,
                collection_name="transaction_categories",
                key_fn=lambda record: (
                    record.transaction_type_code,
                    record.transaction_category_code,
                ),
                key_label="transaction_type_code + transaction_category_code",
            ),
            category_balances=_build_composite_index(
                category_balances,
                collection_name="category_balances",
                key_fn=lambda record: (
                    record.account_id,
                    record.transaction_type_code,
                    record.transaction_category_code,
                ),
                key_label="account_id + transaction_type_code + transaction_category_code",
            ),
            transactions=transactions,
        )


def _require_code(value: str, *, pattern: re.Pattern[str], message: str) -> str:
    normalized = value.strip()
    if not pattern.fullmatch(normalized):
        raise TransactionValidationError(message)
    return normalized


def _require_text(
    value: str,
    *,
    blank_message: str,
    too_long_message: str,
    max_length: int,
) -> str:
    normalized = value.strip()
    if normalized == "":
        raise TransactionValidationError(blank_message)
    if len(normalized) > max_length:
        raise TransactionValidationError(too_long_message)
    return normalized


def _parse_amount(value: str) -> Decimal:
    normalized = value.strip()
    if normalized == "":
        raise TransactionValidationError("Amount cannot be empty.")
    if normalized[0] not in {"+", "-"}:
        raise TransactionValidationError("Amount must start with + or -.")
    if not _AMOUNT_PATTERN.fullmatch(normalized):
        raise TransactionValidationError("Amount should be in format -99999999.99.")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as error:
        raise TransactionValidationError(
            "Amount should be in format -99999999.99."
        ) from error
    if amount.as_tuple().exponent != -2:
        raise TransactionValidationError("Amount should be in format -99999999.99.")
    return amount


def _parse_entry_date(value: str, *, invalid_message: str) -> date:
    normalized = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        raise TransactionValidationError(invalid_message)
    try:
        return date.fromisoformat(normalized)
    except ValueError as error:
        raise TransactionValidationError(invalid_message) from error


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
            raise TransactionStoreConsistencyError(
                f"Store {collection_name} row at index {index} is invalid: {error}"
            ) from error
    return records


def _build_unique_index[T: BaseModel](
    records: list[T],
    *,
    key_name: str,
    collection_name: str,
) -> dict[str, T]:
    index: dict[str, T] = {}
    for record in records:
        key = getattr(record, key_name)
        if key in index:
            raise TransactionStoreConsistencyError(
                f"Store {collection_name} contains duplicate {key_name} {key!r}."
            )
        index[key] = record
    return index


def _build_composite_index[T, K](
    records: list[T],
    *,
    collection_name: str,
    key_fn: Callable[[T], K],
    key_label: str,
) -> dict[K, T]:
    index: dict[K, T] = {}
    for record in records:
        key = key_fn(record)
        if key in index:
            raise TransactionStoreConsistencyError(
                f"Store {collection_name} contains duplicate {key_label} {key!r}."
            )
        index[key] = record
    return index


def _assign_next_transaction_id(transactions: list[TransactionRecord]) -> str:
    last_numeric_transaction_id = 0
    for transaction in transactions:
        if transaction.transaction_id.isdigit():
            last_numeric_transaction_id = int(transaction.transaction_id)
    return str(last_numeric_transaction_id + 1).zfill(16)
