"""Lookup services derived from GNUCobol account and card inquiry behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.accounts import AccountRecord, CardAccountXrefRecord, CardRecord
from app.domain.customers import CustomerRecord
from app.models import StoragePaths
from app.storage import read_store


class LookupError(RuntimeError):
    """Base error for customer, account, and card lookup failures."""


class LookupInputError(LookupError):
    """Raised when the caller does not supply a valid lookup key."""


class LookupNotFoundError(LookupError):
    """Raised when the requested record does not exist."""


class InactiveRecordError(LookupError):
    """Raised when the primary resolved account or card is inactive."""


class AmbiguousLookupError(LookupError):
    """Raised when a supposedly unique lookup target resolves to multiple rows."""


class LookupStoreConsistencyError(LookupError):
    """Raised when persisted lookup data cannot be resolved deterministically."""


class AccountLookupResult(BaseModel):
    """Resolved account-centric lookup result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account: AccountRecord
    card_account_xref: CardAccountXrefRecord | None = None
    customer: CustomerRecord | None = None


class CardLookupResult(BaseModel):
    """Resolved card-centric lookup result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    card: CardRecord
    account: AccountRecord
    card_account_xref: CardAccountXrefRecord | None = None
    customer: CustomerRecord | None = None


class CustomerLookupResult(BaseModel):
    """Resolved customer lookup result plus related account/card rows."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    customer: CustomerRecord
    card_account_xref: list[CardAccountXrefRecord]
    accounts: list[AccountRecord]
    cards: list[CardRecord]


@dataclass(slots=True, frozen=True)
class _LookupSnapshot:
    customers: list[CustomerRecord]
    accounts: list[AccountRecord]
    cards: list[CardRecord]
    card_account_xref: list[CardAccountXrefRecord]


class LookupService:
    """Storage-backed lookup behavior for account, customer, and card inquiries."""

    def __init__(self, paths: StoragePaths) -> None:
        self._paths = paths

    def lookup_account(
        self,
        *,
        account_id: str | None = None,
        card_number: str | None = None,
    ) -> AccountLookupResult:
        """Resolve an account by account ID or card number."""
        normalized_account_id = _normalize_identifier(account_id)
        normalized_card_number = _normalize_identifier(card_number)
        if normalized_account_id is None and normalized_card_number is None:
            raise LookupInputError(
                "You must supply an account ID or a card number."
            )

        snapshot = self._load_snapshot()
        account_by_id = _build_unique_index(
            snapshot.accounts,
            key_name="account_id",
            collection_name="accounts",
        )
        customer_by_id = _build_unique_index(
            snapshot.customers,
            key_name="customer_id",
            collection_name="customers",
        )

        xref_record: CardAccountXrefRecord | None = None
        resolved_account_id = normalized_account_id
        if normalized_account_id is None:
            xref_record = _find_first(
                snapshot.card_account_xref,
                lambda record: record.card_number == normalized_card_number,
            )
            if xref_record is None:
                raise LookupNotFoundError(
                    f"No card/account cross reference found for card number "
                    f"{normalized_card_number!r}."
                )
            resolved_account_id = xref_record.account_id
        else:
            xref_record = _find_first(
                snapshot.card_account_xref,
                lambda record: record.account_id == normalized_account_id,
            )
        if resolved_account_id is None:
            raise LookupInputError("You must supply an account ID or a card number.")

        account = account_by_id.get(resolved_account_id)
        if account is None:
            raise LookupNotFoundError(f"Account {resolved_account_id!r} was not found.")
        if not account.is_active:
            raise InactiveRecordError(f"Account {account.account_id!r} is inactive.")

        customer = None
        if xref_record is not None:
            customer = customer_by_id.get(xref_record.customer_id)

        return AccountLookupResult(
            account=account,
            card_account_xref=xref_record,
            customer=customer,
        )

    def lookup_customer(self, customer_id: str) -> CustomerLookupResult:
        """Resolve a customer plus all related accounts and cards in store order."""
        normalized_customer_id = _require_identifier(customer_id, field_name="customer ID")
        snapshot = self._load_snapshot()
        customer_by_id = _build_unique_index(
            snapshot.customers,
            key_name="customer_id",
            collection_name="customers",
        )
        account_by_id = _build_unique_index(
            snapshot.accounts,
            key_name="account_id",
            collection_name="accounts",
        )
        card_by_number = _build_unique_index(
            snapshot.cards,
            key_name="card_number",
            collection_name="cards",
        )

        customer = customer_by_id.get(normalized_customer_id)
        if customer is None:
            raise LookupNotFoundError(
                f"Customer {normalized_customer_id!r} was not found."
            )

        related_xrefs = [
            record
            for record in snapshot.card_account_xref
            if record.customer_id == normalized_customer_id
        ]
        accounts: list[AccountRecord] = []
        seen_account_ids: set[str] = set()
        cards: list[CardRecord] = []
        seen_card_numbers: set[str] = set()

        for xref_record in related_xrefs:
            if xref_record.account_id not in seen_account_ids:
                account = account_by_id.get(xref_record.account_id)
                if account is None:
                    raise LookupStoreConsistencyError(
                        "Customer lookup references missing account "
                        f"{xref_record.account_id!r} for customer "
                        f"{normalized_customer_id!r}."
                    )
                accounts.append(account)
                seen_account_ids.add(xref_record.account_id)
            if xref_record.card_number not in seen_card_numbers:
                card = card_by_number.get(xref_record.card_number)
                if card is None:
                    raise LookupStoreConsistencyError(
                        "Customer lookup references missing card "
                        f"{xref_record.card_number!r} for customer "
                        f"{normalized_customer_id!r}."
                    )
                cards.append(card)
                seen_card_numbers.add(xref_record.card_number)

        return CustomerLookupResult(
            customer=customer,
            card_account_xref=related_xrefs,
            accounts=accounts,
            cards=cards,
        )

    def lookup_card(
        self,
        *,
        account_id: str | None = None,
        card_number: str | None = None,
    ) -> CardLookupResult:
        """Resolve a card by account ID or card number."""
        normalized_account_id = _normalize_identifier(account_id)
        normalized_card_number = _normalize_identifier(card_number)
        if normalized_account_id is None and normalized_card_number is None:
            raise LookupInputError(
                "You must supply an account ID or a card number."
            )

        snapshot = self._load_snapshot()
        account_by_id = _build_unique_index(
            snapshot.accounts,
            key_name="account_id",
            collection_name="accounts",
        )
        card_by_number = _build_unique_index(
            snapshot.cards,
            key_name="card_number",
            collection_name="cards",
        )
        customer_by_id = _build_unique_index(
            snapshot.customers,
            key_name="customer_id",
            collection_name="customers",
        )

        xref_record: CardAccountXrefRecord | None = None
        resolved_card_number = normalized_card_number
        if normalized_card_number is not None:
            xref_record = _find_first(
                snapshot.card_account_xref,
                lambda record: record.card_number == normalized_card_number,
            )
            if xref_record is not None:
                if (
                    normalized_account_id is not None
                    and xref_record.account_id != normalized_account_id
                ):
                    raise LookupInputError(
                        "Supplied account ID does not match the card number."
                    )
                if normalized_account_id is None:
                    normalized_account_id = xref_record.account_id
        else:
            xref_record = _find_first(
                snapshot.card_account_xref,
                lambda record: record.account_id == normalized_account_id,
            )
            if xref_record is None:
                raise LookupNotFoundError(
                    f"No card/account cross reference found for account ID "
                    f"{normalized_account_id!r}."
                )
            resolved_card_number = xref_record.card_number
        if resolved_card_number is None:
            raise LookupInputError("You must supply an account ID or a card number.")

        card = card_by_number.get(resolved_card_number)
        if card is None:
            raise LookupNotFoundError(f"Card {resolved_card_number!r} was not found.")
        if not card.is_active:
            raise InactiveRecordError(f"Card {card.card_number!r} is inactive.")

        resolved_account = account_by_id.get(card.account_id)
        if resolved_account is None:
            raise LookupStoreConsistencyError(
                f"Card {card.card_number!r} references missing account "
                f"{card.account_id!r}."
            )
        if not resolved_account.is_active:
            raise InactiveRecordError(
                f"Account {resolved_account.account_id!r} is inactive."
            )

        customer = None
        if xref_record is not None:
            customer = customer_by_id.get(xref_record.customer_id)

        return CardLookupResult(
            card=card,
            account=resolved_account,
            card_account_xref=xref_record,
            customer=customer,
        )

    def _load_snapshot(self) -> _LookupSnapshot:
        store = read_store(self._paths)
        return _LookupSnapshot(
            customers=_validate_collection(
                store["customers"],
                CustomerRecord,
                collection_name="customers",
            ),
            accounts=_validate_collection(
                store["accounts"],
                AccountRecord,
                collection_name="accounts",
            ),
            cards=_validate_collection(
                store["cards"],
                CardRecord,
                collection_name="cards",
            ),
            card_account_xref=_validate_collection(
                store["card_account_xref"],
                CardAccountXrefRecord,
                collection_name="card_account_xref",
            ),
        )


def _normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _require_identifier(value: str | None, *, field_name: str) -> str:
    normalized = _normalize_identifier(value)
    if normalized is None:
        raise LookupInputError(f"You must supply a {field_name}.")
    return normalized


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
            raise LookupStoreConsistencyError(
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
            raise AmbiguousLookupError(
                f"Store {collection_name} contains duplicate {key_name} {key!r}."
            )
        index[key] = record
    return index


def _find_first[T](records: list[T], predicate: Callable[[T], bool]) -> T | None:
    for record in records:
        if predicate(record):
            return record
    return None
