from __future__ import annotations

from pathlib import Path
import re

import pytest

from app.domain.accounts import parse_account_record
from app.domain.transactions_activity import parse_report_request_record
from app.domain.users import parse_user_security_record
from app.importing import LineParser, SeedImportError, parse_lines_strict


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_seed_line(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return handle.readline().rstrip("\n")


def test_parse_lines_strict_returns_records_for_valid_lines() -> None:
    line = _read_seed_line("app/data/ASCII.seed/usrsec.dat")

    result = parse_lines_strict(
        [line],
        source_name="usrsec.dat",
        parser=parse_user_security_record,
    )

    assert len(result.records) == 1
    assert result.records[0].user_id == "ADMIN001"
    assert result.malformed_lines == []


@pytest.mark.parametrize(
    ("source_name", "lines", "parser", "expected_message", "expected_raw_line"),
    [
            (
                "usrsec.dat",
                [_read_seed_line("app/data/ASCII.seed/usrsec.dat"), " " * 80],
                parse_user_security_record,
                "usrsec.dat: line 2 rejected: Line 2: SEC-USR-ID is blank.",
                " " * 80,
            ),
            (
                "acctdata.txt",
                ["1" * 301],
                parse_account_record,
                "acctdata.txt: line 1 rejected: Line 1: expected at most 300 characters, received 301.",
                "1" * 301,
            ),
            (
                "tranrept_requests.txt",
                ["2024-05-01 12:00:00|A00001|Weekly|2024-05-01|2024-05-31"],
                parse_report_request_record,
                "tranrept_requests.txt: line 1 rejected: Line 1: unsupported REQUEST-REPORT-NAME 'Weekly'; expected one of Monthly, Yearly, Custom.",
                "2024-05-01 12:00:00|A00001|Weekly|2024-05-01|2024-05-31",
            ),
        ],
    )
def test_parse_lines_strict_raises_seed_import_error_with_detail(
    source_name: str,
    lines: list[str],
    parser: LineParser[object],
    expected_message: str,
    expected_raw_line: str,
) -> None:
    with pytest.raises(SeedImportError, match=re.escape(expected_message)) as error_info:
        parse_lines_strict(
            lines,
            source_name=source_name,
            parser=parser,
        )

    assert error_info.value.detail.source_name == source_name
    assert error_info.value.detail.raw_line == expected_raw_line
    assert error_info.value.detail.reason in str(error_info.value)
