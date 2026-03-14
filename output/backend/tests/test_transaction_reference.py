from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import pytest

from app.domain.transactions_reference import (
    CATEGORY_BALANCE_RECORD_WIDTH,
    DISCLOSURE_GROUP_RECORD_WIDTH,
    TRANSACTION_CATEGORY_RECORD_WIDTH,
    TRANSACTION_TYPE_RECORD_WIDTH,
    TransactionReferenceParseError,
    parse_category_balance_record,
    parse_disclosure_group_record,
    parse_transaction_category_record,
    parse_transaction_type_record,
)

Parser = Callable[[str], object]


def _build_category_balance_line(
    *,
    account_id: str,
    transaction_type_code: str,
    transaction_category_code: str,
    balance: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            account_id.ljust(11),
            transaction_type_code.ljust(2),
            transaction_category_code.ljust(4),
            balance.ljust(11),
            filler.ljust(22),
        ],
    )


def _build_disclosure_group_line(
    *,
    account_group_id: str,
    transaction_type_code: str,
    transaction_category_code: str,
    interest_rate: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            account_group_id.ljust(10),
            transaction_type_code.ljust(2),
            transaction_category_code.ljust(4),
            interest_rate.ljust(6),
            filler.ljust(28),
        ],
    )


def _build_transaction_type_line(
    *,
    transaction_type_code: str,
    description: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            transaction_type_code.ljust(2),
            description.ljust(50),
            filler.ljust(8),
        ],
    )


def _build_transaction_category_line(
    *,
    transaction_type_code: str,
    transaction_category_code: str,
    description: str,
    filler: str = "",
) -> str:
    return "".join(
        [
            transaction_type_code.ljust(2),
            transaction_category_code.ljust(4),
            description.ljust(50),
            filler.ljust(4),
        ],
    )


def test_parse_category_balance_record_from_seed_line() -> None:
    record = parse_category_balance_record("000000000010100010000000000{0000000000000000000000")

    assert record.account_id == "00000000001"
    assert record.transaction_type_code == "01"
    assert record.transaction_category_code == "0001"
    assert record.balance == Decimal("0.00")
    assert record.filler == "0000000000000000000000"


def test_parse_disclosure_group_record_from_seed_line() -> None:
    record = parse_disclosure_group_record("A00000000001000100150{0000000000000000000000000000")

    assert record.account_group_id == "A000000000"
    assert record.transaction_type_code == "01"
    assert record.transaction_category_code == "0001"
    assert record.interest_rate == Decimal("15.00")
    assert record.filler == "0000000000000000000000000000"


def test_parse_transaction_type_record_from_seed_line() -> None:
    record = parse_transaction_type_record("01Purchase                                          00000000")

    assert record.transaction_type_code == "01"
    assert record.description == "Purchase"
    assert record.filler == "00000000"


def test_parse_transaction_category_record_from_seed_line() -> None:
    record = parse_transaction_category_record(
        "010001Regular Sales Draft                               0000",
    )

    assert record.transaction_type_code == "01"
    assert record.transaction_category_code == "0001"
    assert record.description == "Regular Sales Draft"
    assert record.filler == "0000"


def test_parse_reference_records_support_negative_signed_amounts() -> None:
    category_balance = parse_category_balance_record(
        _build_category_balance_line(
            account_id="00000000123",
            transaction_type_code="05",
            transaction_category_code="0005",
            balance="0000000012R",
        ),
    )
    disclosure_group = parse_disclosure_group_record(
        _build_disclosure_group_line(
            account_group_id="VIPGROUP",
            transaction_type_code="05",
            transaction_category_code="0005",
            interest_rate="0012R",
        ),
    )

    assert len(_build_category_balance_line(
        account_id="00000000123",
        transaction_type_code="05",
        transaction_category_code="0005",
        balance="0000000012R",
    )) == CATEGORY_BALANCE_RECORD_WIDTH
    assert len(_build_disclosure_group_line(
        account_group_id="VIPGROUP",
        transaction_type_code="05",
        transaction_category_code="0005",
        interest_rate="0012R",
    )) == DISCLOSURE_GROUP_RECORD_WIDTH
    assert category_balance.balance == Decimal("-1.29")
    assert disclosure_group.interest_rate == Decimal("-1.29")


@pytest.mark.parametrize(
    ("parser", "line", "expected_message"),
    [
        (
            parse_category_balance_record,
            _build_category_balance_line(
                account_id="0000000012A",
                transaction_type_code="01",
                transaction_category_code="0001",
                balance="0000000000{",
            ),
            "Line 1: TRANCAT-ACCT-ID must contain only digits, received '0000000012A'.",
        ),
        (
            parse_category_balance_record,
            _build_category_balance_line(
                account_id="00000000123",
                transaction_type_code="01",
                transaction_category_code="00A1",
                balance="0000000000{",
            ),
            "Line 1: TRANCAT-CD must contain only digits, received '00A1'.",
        ),
        (
            parse_category_balance_record,
            _build_category_balance_line(
                account_id="00000000123",
                transaction_type_code="01",
                transaction_category_code="0001",
                balance="0000000000X",
            ),
            "Line 1: TRAN-CAT-BAL has unsupported signed-digit suffix 'X' in '0000000000X'.",
        ),
        (
            parse_disclosure_group_record,
            _build_disclosure_group_line(
                account_group_id="",
                transaction_type_code="01",
                transaction_category_code="0001",
                interest_rate="00150{",
            ),
            "Line 1: DIS-ACCT-GROUP-ID is blank.",
        ),
        (
            parse_disclosure_group_record,
            _build_disclosure_group_line(
                account_group_id="A000000000",
                transaction_type_code="01",
                transaction_category_code="0001",
                interest_rate="0015X{",
            ),
            "Line 1: DIS-INT-RATE must contain digits before the signed suffix, received '0015X{'.",
        ),
        (
            parse_transaction_type_record,
            _build_transaction_type_line(transaction_type_code="", description="Purchase"),
            "Line 1: TRAN-TYPE is blank.",
        ),
        (
            parse_transaction_type_record,
            _build_transaction_type_line(transaction_type_code="01", description="") + "X",
            "Line 1: expected at most 60 characters, received 61.",
        ),
        (
            parse_transaction_category_record,
            _build_transaction_category_line(
                transaction_type_code="01",
                transaction_category_code="0A01",
                description="Regular Sales Draft",
            ),
            "Line 1: TRAN-CAT-CD must contain only digits, received '0A01'.",
        ),
        (
            parse_transaction_category_record,
            _build_transaction_category_line(
                transaction_type_code="01",
                transaction_category_code="0001",
                description="",
            ),
            "Line 1: TRAN-CAT-TYPE-DESC is blank.",
        ),
    ],
)
def test_parse_reference_records_reject_malformed_lines(
    parser: Parser,
    line: str,
    expected_message: str,
) -> None:
    with pytest.raises(TransactionReferenceParseError, match=expected_message):
        parser(line)


def test_reference_record_builder_widths_match_copybooks() -> None:
    assert len(
        _build_category_balance_line(
            account_id="00000000123",
            transaction_type_code="01",
            transaction_category_code="0001",
            balance="0000000000{",
        ),
    ) == CATEGORY_BALANCE_RECORD_WIDTH
    assert len(
        _build_disclosure_group_line(
            account_group_id="A000000000",
            transaction_type_code="01",
            transaction_category_code="0001",
            interest_rate="00150{",
        ),
    ) == DISCLOSURE_GROUP_RECORD_WIDTH
    assert len(
        _build_transaction_type_line(
            transaction_type_code="01",
            description="Purchase",
        ),
    ) == TRANSACTION_TYPE_RECORD_WIDTH
    assert len(
        _build_transaction_category_line(
            transaction_type_code="01",
            transaction_category_code="0001",
            description="Regular Sales Draft",
        ),
    ) == TRANSACTION_CATEGORY_RECORD_WIDTH
