from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest

from app.domain.accounts import (
    ACCOUNT_RECORD_WIDTH,
    CARD_ACCOUNT_XREF_RECORD_WIDTH,
    CARD_RECORD_WIDTH,
    AccountActiveStatus,
    AccountCardParseError,
    CardActiveStatus,
    parse_account_record,
    parse_card_account_xref_record,
    parse_card_record,
)

Parser = Callable[[str], object]


def _build_account_line(
    *,
    account_id: str,
    active_status: str,
    current_balance: str,
    credit_limit: str,
    cash_credit_limit: str,
    open_date: str,
    expiration_date: str,
    reissue_date: str,
    current_cycle_credit: str,
    current_cycle_debit: str,
    billing_postal_code: str,
    group_id: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            account_id.ljust(11),
            active_status.ljust(1),
            current_balance.ljust(12),
            credit_limit.ljust(12),
            cash_credit_limit.ljust(12),
            open_date.ljust(10),
            expiration_date.ljust(10),
            reissue_date.ljust(10),
            current_cycle_credit.ljust(12),
            current_cycle_debit.ljust(12),
            billing_postal_code.ljust(10),
            group_id.ljust(10),
            filler.ljust(178),
        ],
    )


def _build_card_line(
    *,
    card_number: str,
    account_id: str,
    cvv_code: str,
    embossed_name: str,
    expiration_date: str,
    active_status: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            card_number.ljust(16),
            account_id.ljust(11),
            cvv_code.ljust(3),
            embossed_name.ljust(50),
            expiration_date.ljust(10),
            active_status.ljust(1),
            filler.ljust(59),
        ],
    )


def _build_card_xref_line(
    *,
    card_number: str,
    customer_id: str,
    account_id: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            card_number.ljust(16),
            customer_id.ljust(9),
            account_id.ljust(11),
            filler.ljust(14),
        ],
    )


def test_parse_account_record_from_seed_line() -> None:
    record = parse_account_record(
        "00000000001Y00000001940{00000020200{00000010200{2014-11-212026-05-212026-05-21"
        "00000000000{00000000000{A000000000VIPGROUP",
    )

    assert record.account_id == "00000000001"
    assert record.active_status is AccountActiveStatus.ACTIVE
    assert record.is_active is True
    assert record.current_balance == Decimal("194.00")
    assert record.credit_limit == Decimal("2020.00")
    assert record.cash_credit_limit == Decimal("1020.00")
    assert record.open_date == date(2014, 11, 21)
    assert record.expiration_date == date(2026, 5, 21)
    assert record.reissue_date == date(2026, 5, 21)
    assert record.current_cycle_credit == Decimal("0.00")
    assert record.current_cycle_debit == Decimal("0.00")
    assert record.billing_postal_code == "A000000000"
    assert record.group_id == "VIPGROUP"
    assert record.filler is None


def test_parse_account_record_supports_negative_signed_amounts() -> None:
    line = _build_account_line(
        account_id="00000000077",
        active_status="Y",
        current_balance="00000001234N",
        credit_limit="00000099999{",
        cash_credit_limit="00000010000{",
        open_date="2024-01-01",
        expiration_date="2028-01-01",
        reissue_date="2026-01-01",
        current_cycle_credit="00000000000{",
        current_cycle_debit="00000000012R",
        billing_postal_code="90210",
        group_id="",
    )

    record = parse_account_record(line)

    assert len(line) == ACCOUNT_RECORD_WIDTH
    assert record.current_balance == Decimal("-123.45")
    assert record.current_cycle_debit == Decimal("-1.29")
    assert record.group_id is None


def test_parse_card_record_from_seed_line() -> None:
    record = parse_card_record(
        "050002445376574000000000050747Aniya Von                                         "
        "2023-03-09Y                                                           ",
    )

    assert record.card_number == "0500024453765740"
    assert record.account_id == "00000000050"
    assert record.cvv_code == "747"
    assert record.embossed_name == "Aniya Von"
    assert record.expiration_date == date(2023, 3, 9)
    assert record.active_status is CardActiveStatus.ACTIVE
    assert record.is_active is True
    assert record.filler is None


def test_parse_card_account_xref_record_from_seed_line() -> None:
    record = parse_card_account_xref_record("050002445376574000000005000000000050")

    assert record.card_number == "0500024453765740"
    assert record.customer_id == "000000050"
    assert record.account_id == "00000000050"
    assert record.filler is None


@pytest.mark.parametrize(
    ("parser", "line", "expected_message"),
    [
        (
            parse_account_record,
            _build_account_line(
                account_id="00000000088",
                active_status="N",
                current_balance="00000001000{",
                credit_limit="00000002000{",
                cash_credit_limit="00000000500{",
                open_date="2024-01-01",
                expiration_date="2028-01-01",
                reissue_date="2026-01-01",
                current_cycle_credit="00000000000{",
                current_cycle_debit="00000000000{",
                billing_postal_code="90210",
                group_id="",
            ),
            "Line 1: unsupported ACCT-ACTIVE-STATUS 'N'; expected 'Y'.",
        ),
        (
            parse_account_record,
            _build_account_line(
                account_id="00000000089",
                active_status="Y",
                current_balance="00000001000X",
                credit_limit="00000002000{",
                cash_credit_limit="00000000500{",
                open_date="2024-01-01",
                expiration_date="2028-01-01",
                reissue_date="2026-01-01",
                current_cycle_credit="00000000000{",
                current_cycle_debit="00000000000{",
                billing_postal_code="90210",
                group_id="",
            ),
            "Line 1: ACCT-CURR-BAL has unsupported signed-digit suffix 'X' in '00000001000X'.",
        ),
        (
            parse_card_record,
            _build_card_line(
                card_number="0500024453765740",
                account_id="00000000005",
                cvv_code="74A",
                embossed_name="Aniya Von",
                expiration_date="2023-03-09",
                active_status="Y",
            ),
            "Line 1: CARD-CVV-CD must contain only digits, received '74A'.",
        ),
        (
            parse_card_record,
            _build_card_line(
                card_number="0500024453765740",
                account_id="00000000005",
                cvv_code="747",
                embossed_name="Aniya Von",
                expiration_date="2023-03-09",
                active_status="N",
            ),
            "Line 1: unsupported CARD-ACTIVE-STATUS 'N'; expected 'Y'.",
        ),
        (
            parse_card_account_xref_record,
            _build_card_xref_line(
                card_number="05000244537657AA",
                customer_id="000000005",
                account_id="00000000005",
            ),
            "Line 1: XREF-CARD-NUM must contain only digits, received '05000244537657AA'.",
        ),
        (
            parse_card_account_xref_record,
            _build_card_xref_line(
                card_number="0500024453765740",
                customer_id="000000005",
                account_id="00000000005",
            )
            + "X",
            "Line 1: expected at most 50 characters, received 51.",
        ),
    ],
)
def test_parse_account_card_records_reject_malformed_lines(
    parser: Parser,
    line: str,
    expected_message: str,
) -> None:
    with pytest.raises(AccountCardParseError, match=expected_message):
        parser(line)
