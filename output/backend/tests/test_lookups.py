from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.accounts import (
    AccountActiveStatus,
    AccountRecord,
    CardAccountXrefRecord,
    CardActiveStatus,
    CardRecord,
)
from app.domain.customers import (
    CustomerAddress,
    CustomerContact,
    CustomerName,
    CustomerRecord,
    PrimaryCardHolderIndicator,
)
from app.domain.lookups import (
    AmbiguousLookupError,
    InactiveRecordError,
    LookupInputError,
    LookupNotFoundError,
    LookupService,
    LookupStoreConsistencyError,
)
from app.models import default_store_document
from app.storage import write_store


def test_lookup_account_resolves_account_customer_and_first_xref(storage_paths) -> None:
    payload = _build_lookup_store()
    payload["card_account_xref"].append(
        CardAccountXrefRecord(
            card_number="4999999999999999",
            customer_id="000000001",
            account_id="00000000001",
        ).model_dump(mode="python")
    )
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)
    result = service.lookup_account(account_id="00000000001")

    assert result.account.account_id == "00000000001"
    assert result.customer is not None
    assert result.customer.customer_id == "000000001"
    assert result.card_account_xref is not None
    assert result.card_account_xref.card_number == "4111111111111111"


def test_lookup_account_by_card_requires_xref_match(storage_paths) -> None:
    payload = _build_lookup_store()
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)
    result = service.lookup_account(card_number="4111111111111111")

    assert result.account.account_id == "00000000001"
    assert result.card_account_xref is not None
    assert result.card_account_xref.customer_id == "000000001"


def test_lookup_customer_returns_related_records_in_xref_order(storage_paths) -> None:
    payload = _build_lookup_store()
    payload["accounts"].append(
        _account_record(account_id="00000000002").model_dump(mode="python")
    )
    payload["cards"].append(
        _card_record(
            card_number="4222222222222222",
            account_id="00000000002",
            embossed_name="Ada Lovelace",
        ).model_dump(mode="python")
    )
    payload["card_account_xref"].append(
        CardAccountXrefRecord(
            card_number="4222222222222222",
            customer_id="000000001",
            account_id="00000000002",
        ).model_dump(mode="python")
    )
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)
    result = service.lookup_customer("000000001")

    assert result.customer.customer_id == "000000001"
    assert [record.account_id for record in result.accounts] == [
        "00000000001",
        "00000000002",
    ]
    assert [record.card_number for record in result.cards] == [
        "4111111111111111",
        "4222222222222222",
    ]


def test_lookup_card_rejects_mismatched_account_and_card_inputs(storage_paths) -> None:
    payload = _build_lookup_store()
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)

    with pytest.raises(
        LookupInputError,
        match="Supplied account ID does not match the card number.",
    ):
        service.lookup_card(
            account_id="00000000099",
            card_number="4111111111111111",
        )


def test_lookup_card_by_account_uses_first_xref_and_resolves_account(storage_paths) -> None:
    payload = _build_lookup_store()
    payload["card_account_xref"].append(
        CardAccountXrefRecord(
            card_number="4999999999999999",
            customer_id="000000001",
            account_id="00000000001",
        ).model_dump(mode="python")
    )
    payload["cards"].append(
        _card_record(
            card_number="4999999999999999",
            account_id="00000000001",
            embossed_name="Grace Hopper",
        ).model_dump(mode="python")
    )
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)
    result = service.lookup_card(account_id="00000000001")

    assert result.card.card_number == "4111111111111111"
    assert result.account.account_id == "00000000001"
    assert result.customer is not None
    assert result.customer.customer_id == "000000001"


@pytest.mark.parametrize(
    ("lookup_call", "expected_error", "expected_message"),
    [
        (
            lambda service: service.lookup_account(),
            LookupInputError,
            "You must supply an account ID or a card number.",
        ),
        (
            lambda service: service.lookup_card(),
            LookupInputError,
            "You must supply an account ID or a card number.",
        ),
        (
            lambda service: service.lookup_customer(" "),
            LookupInputError,
            "You must supply a customer ID.",
        ),
        (
            lambda service: service.lookup_account(card_number="4000000000000000"),
            LookupNotFoundError,
            "No card/account cross reference found for card number '4000000000000000'.",
        ),
        (
            lambda service: service.lookup_card(account_id="00000000999"),
            LookupNotFoundError,
            "No card/account cross reference found for account ID '00000000999'.",
        ),
        (
            lambda service: service.lookup_customer("000000999"),
            LookupNotFoundError,
            "Customer '000000999' was not found.",
        ),
    ],
)
def test_lookup_services_reject_missing_inputs_and_missing_rows(
    storage_paths,
    lookup_call,
    expected_error,
    expected_message: str,
) -> None:
    payload = _build_lookup_store()
    write_store(storage_paths, payload)
    service = LookupService(storage_paths)

    with pytest.raises(expected_error, match=expected_message):
        lookup_call(service)


def test_lookup_account_rejects_inactive_accounts(storage_paths) -> None:
    payload = _build_lookup_store()
    inactive_account = _account_record(account_id="00000000077").model_dump(mode="python")
    inactive_account["is_active"] = False
    payload["accounts"] = [inactive_account]
    payload["card_account_xref"] = [
        CardAccountXrefRecord(
            card_number="4777777777777777",
            customer_id="000000001",
            account_id="00000000077",
        ).model_dump(mode="python")
    ]
    payload["cards"] = [
        _card_record(
            card_number="4777777777777777",
            account_id="00000000077",
            embossed_name="Inactive Holder",
        ).model_dump(mode="python")
    ]
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)

    with pytest.raises(
        InactiveRecordError,
        match="Account '00000000077' is inactive.",
    ):
        service.lookup_account(account_id="00000000077")


def test_lookup_card_rejects_inactive_cards(storage_paths) -> None:
    payload = _build_lookup_store()
    inactive_card = _card_record(
        card_number="4888888888888888",
        account_id="00000000001",
        embossed_name="Inactive Card",
    ).model_dump(mode="python")
    inactive_card["is_active"] = False
    payload["cards"] = [inactive_card]
    payload["card_account_xref"] = [
        CardAccountXrefRecord(
            card_number="4888888888888888",
            customer_id="000000001",
            account_id="00000000001",
        ).model_dump(mode="python")
    ]
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)

    with pytest.raises(
        InactiveRecordError,
        match="Card '4888888888888888' is inactive.",
    ):
        service.lookup_card(card_number="4888888888888888")


def test_lookup_service_rejects_duplicate_primary_keys(storage_paths) -> None:
    payload = _build_lookup_store()
    payload["accounts"].append(
        _account_record(account_id="00000000001").model_dump(mode="python")
    )
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)

    with pytest.raises(
        AmbiguousLookupError,
        match="Store accounts contains duplicate account_id '00000000001'.",
    ):
        service.lookup_account(account_id="00000000001")


def test_lookup_customer_rejects_broken_related_joins(storage_paths) -> None:
    payload = _build_lookup_store()
    payload["card_account_xref"] = [
        CardAccountXrefRecord(
            card_number="4111111111111111",
            customer_id="000000001",
            account_id="00000000999",
        ).model_dump(mode="python")
    ]
    write_store(storage_paths, payload)

    service = LookupService(storage_paths)

    with pytest.raises(
        LookupStoreConsistencyError,
        match=(
            "Customer lookup references missing account '00000000999' "
            "for customer '000000001'."
        ),
    ):
        service.lookup_customer("000000001")


def _build_lookup_store() -> dict[str, object]:
    payload = default_store_document()
    payload["customers"] = [_customer_record().model_dump(mode="python")]
    payload["accounts"] = [_account_record().model_dump(mode="python")]
    payload["cards"] = [_card_record().model_dump(mode="python")]
    payload["card_account_xref"] = [
        CardAccountXrefRecord(
            card_number="4111111111111111",
            customer_id="000000001",
            account_id="00000000001",
        ).model_dump(mode="python")
    ]
    return payload


def _customer_record() -> CustomerRecord:
    return CustomerRecord(
        customer_id="000000001",
        name=CustomerName(first_name="Ada", middle_name=None, last_name="Lovelace"),
        address=CustomerAddress(
            line_1="12 Logic Ave",
            line_2=None,
            line_3=None,
            state_code="NY",
            country_code="USA",
            postal_code="10001",
        ),
        contact=CustomerContact(
            primary_phone="555-1000",
            secondary_phone=None,
            social_security_number="123456789",
            government_issued_id=None,
            eft_account_id=None,
        ),
        date_of_birth=date(1980, 12, 17),
        primary_card_holder_indicator=PrimaryCardHolderIndicator.YES,
        is_primary_card_holder=True,
        fico_credit_score=801,
        filler=None,
    )


def _account_record(*, account_id: str = "00000000001") -> AccountRecord:
    return AccountRecord(
        account_id=account_id,
        active_status=AccountActiveStatus.ACTIVE,
        is_active=True,
        current_balance=Decimal("100.00"),
        credit_limit=Decimal("2500.00"),
        cash_credit_limit=Decimal("500.00"),
        open_date=date(2024, 1, 1),
        expiration_date=date(2028, 1, 1),
        reissue_date=date(2026, 1, 1),
        current_cycle_credit=Decimal("0.00"),
        current_cycle_debit=Decimal("0.00"),
        billing_postal_code="10001",
        group_id="VIPGROUP",
        filler=None,
    )


def _card_record(
    *,
    card_number: str = "4111111111111111",
    account_id: str = "00000000001",
    embossed_name: str = "Ada Lovelace",
) -> CardRecord:
    return CardRecord(
        card_number=card_number,
        account_id=account_id,
        cvv_code="123",
        embossed_name=embossed_name,
        expiration_date=date(2028, 1, 1),
        active_status=CardActiveStatus.ACTIVE,
        is_active=True,
        filler=None,
    )
