from __future__ import annotations

from datetime import date

import pytest

from app.domain.customers import (
    CUSTOMER_RECORD_WIDTH,
    CustomerParseError,
    PrimaryCardHolderIndicator,
    parse_customer_record,
)


def _build_customer_line(
    *,
    customer_id: str,
    first_name: str,
    middle_name: str,
    last_name: str,
    line_1: str,
    line_2: str,
    line_3: str,
    state_code: str,
    country_code: str,
    postal_code: str,
    primary_phone: str,
    secondary_phone: str,
    social_security_number: str,
    government_issued_id: str,
    date_of_birth: str,
    eft_account_id: str,
    primary_indicator: str,
    fico_credit_score: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            customer_id.ljust(9),
            first_name.ljust(25),
            middle_name.ljust(25),
            last_name.ljust(25),
            line_1.ljust(50),
            line_2.ljust(50),
            line_3.ljust(50),
            state_code.ljust(2),
            country_code.ljust(3),
            postal_code.ljust(10),
            primary_phone.ljust(15),
            secondary_phone.ljust(15),
            social_security_number.ljust(9),
            government_issued_id.ljust(20),
            date_of_birth.ljust(10),
            eft_account_id.ljust(10),
            primary_indicator.ljust(1),
            fico_credit_score.ljust(3),
            filler.ljust(168),
        ],
    )


def test_parse_customer_record_from_seed_line() -> None:
    record = parse_customer_record(
        "000000001Immanuel                 M                        Kessler                  "
        "742 Modern Lane                                   "
        "Suite 10                                          "
        "Berlin Heights                                    "
        "BEDEU10115     +49-555-0001   +49-555-0002   020973888"
        "000000000000493684371961-06-080053581756Y274",
    )

    assert record.customer_id == "000000001"
    assert record.name.first_name == "Immanuel"
    assert record.name.middle_name == "M"
    assert record.name.last_name == "Kessler"
    assert record.address.line_1 == "742 Modern Lane"
    assert record.address.line_2 == "Suite 10"
    assert record.address.line_3 == "Berlin Heights"
    assert record.address.state_code == "BE"
    assert record.address.country_code == "DEU"
    assert record.address.postal_code == "10115"
    assert record.contact.primary_phone == "+49-555-0001"
    assert record.contact.secondary_phone == "+49-555-0002"
    assert record.contact.social_security_number == "020973888"
    assert record.contact.government_issued_id == "00000000000049368437"
    assert record.contact.eft_account_id == "0053581756"
    assert record.date_of_birth == date(1961, 6, 8)
    assert record.primary_card_holder_indicator is PrimaryCardHolderIndicator.YES
    assert record.is_primary_card_holder is True
    assert record.fico_credit_score == 274
    assert record.filler is None


def test_parse_customer_record_normalizes_optional_blank_fields() -> None:
    line = _build_customer_line(
        customer_id="000000123",
        first_name="Ada",
        middle_name="",
        last_name="Lovelace",
        line_1="12 Logic Ave",
        line_2="",
        line_3="",
        state_code="NY",
        country_code="USA",
        postal_code="10001",
        primary_phone="555-1000",
        secondary_phone="",
        social_security_number="123456789",
        government_issued_id="",
        date_of_birth="1980-12-17",
        eft_account_id="",
        primary_indicator="N",
        fico_credit_score="801",
    )

    record = parse_customer_record(line)

    assert len(line) == CUSTOMER_RECORD_WIDTH
    assert record.name.middle_name is None
    assert record.address.line_2 is None
    assert record.address.line_3 is None
    assert record.contact.secondary_phone is None
    assert record.contact.government_issued_id is None
    assert record.contact.eft_account_id is None
    assert record.primary_card_holder_indicator is PrimaryCardHolderIndicator.NO
    assert record.is_primary_card_holder is False


@pytest.mark.parametrize(
    ("line", "expected_message"),
    [
        (
            _build_customer_line(
                customer_id="000000124",
                first_name="Ada",
                middle_name="",
                last_name="Lovelace",
                line_1="12 Logic Ave",
                line_2="",
                line_3="",
                state_code="NY",
                country_code="USA",
                postal_code="10001",
                primary_phone="555-1000",
                secondary_phone="",
                social_security_number="123456789",
                government_issued_id="",
                date_of_birth="1980-13-17",
                eft_account_id="",
                primary_indicator="Y",
                fico_credit_score="801",
            ),
            "Line 1: CUST-DOB-YYYY-MM-DD must be YYYY-MM-DD, received '1980-13-17'.",
        ),
        (
            _build_customer_line(
                customer_id="000000125",
                first_name="Ada",
                middle_name="",
                last_name="Lovelace",
                line_1="12 Logic Ave",
                line_2="",
                line_3="",
                state_code="NY",
                country_code="USA",
                postal_code="10001",
                primary_phone="555-1000",
                secondary_phone="",
                social_security_number="123456789",
                government_issued_id="",
                date_of_birth="1980-12-17",
                eft_account_id="",
                primary_indicator="X",
                fico_credit_score="801",
            ),
            "Line 1: unsupported CUST-PRI-CARD-HOLDER-IND 'X'; expected 'Y' or 'N'.",
        ),
        (
            _build_customer_line(
                customer_id="00000012A",
                first_name="Ada",
                middle_name="",
                last_name="Lovelace",
                line_1="12 Logic Ave",
                line_2="",
                line_3="",
                state_code="NY",
                country_code="USA",
                postal_code="10001",
                primary_phone="555-1000",
                secondary_phone="",
                social_security_number="123456789",
                government_issued_id="",
                date_of_birth="1980-12-17",
                eft_account_id="",
                primary_indicator="Y",
                fico_credit_score="801",
            ),
            "Line 1: CUST-ID must contain only digits, received '00000012A'.",
        ),
        (
            _build_customer_line(
                customer_id="000000126",
                first_name="Ada",
                middle_name="",
                last_name="",
                line_1="12 Logic Ave",
                line_2="",
                line_3="",
                state_code="NY",
                country_code="USA",
                postal_code="10001",
                primary_phone="555-1000",
                secondary_phone="",
                social_security_number="123456789",
                government_issued_id="",
                date_of_birth="1980-12-17",
                eft_account_id="",
                primary_indicator="Y",
                fico_credit_score="801",
            ),
            "Line 1: CUST-LAST-NAME is blank.",
        ),
        (
            _build_customer_line(
                customer_id="000000127",
                first_name="Ada",
                middle_name="",
                last_name="Lovelace",
                line_1="12 Logic Ave",
                line_2="",
                line_3="",
                state_code="NY",
                country_code="USA",
                postal_code="10001",
                primary_phone="555-1000",
                secondary_phone="",
                social_security_number="123456789",
                government_issued_id="",
                date_of_birth="1980-12-17",
                eft_account_id="",
                primary_indicator="Y",
                fico_credit_score="801",
            )
            + "X",
            "Line 1: expected at most 500 characters, received 501.",
        ),
    ],
)
def test_parse_customer_record_rejects_malformed_lines(
    line: str,
    expected_message: str,
) -> None:
    with pytest.raises(CustomerParseError, match=expected_message):
        parse_customer_record(line)
