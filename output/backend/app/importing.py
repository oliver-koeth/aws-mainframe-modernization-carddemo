"""Shared import-stage helpers for deterministic seed bootstrap behavior."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

ParsedRecord = TypeVar("ParsedRecord")
ParsedRecord_co = TypeVar("ParsedRecord_co", covariant=True)


class LineParser(Protocol[ParsedRecord_co]):
    """Callable parser contract shared by record-family modules."""

    def __call__(self, line: str, *, line_number: int = 1) -> ParsedRecord_co: ...


@dataclass(slots=True, frozen=True)
class MalformedLineDetail:
    """Structured details about one rejected source line."""

    source_name: str
    line_number: int
    raw_line: str
    reason: str


class SeedImportError(RuntimeError):
    """Raised when seed import encounters a malformed line."""

    def __init__(self, detail: MalformedLineDetail) -> None:
        self.detail = detail
        super().__init__(
            f"{detail.source_name}: line {detail.line_number} rejected: {detail.reason}"
        )


@dataclass(slots=True, frozen=True)
class StrictImportResult(Generic[ParsedRecord]):
    """Successful parsed records plus import-time diagnostics."""

    records: list[ParsedRecord]
    malformed_lines: list[MalformedLineDetail]


def parse_lines_strict(
    lines: Iterable[str],
    *,
    source_name: str,
    parser: LineParser[ParsedRecord],
) -> StrictImportResult[ParsedRecord]:
    """Parse lines with a shared hard-fail strategy for malformed records."""
    records: list[ParsedRecord] = []

    for line_number, raw_line in enumerate(lines, start=1):
        try:
            records.append(parser(raw_line, line_number=line_number))
        except ValueError as error:
            detail = MalformedLineDetail(
                source_name=source_name,
                line_number=line_number,
                raw_line=raw_line,
                reason=str(error),
            )
            raise SeedImportError(detail) from error

    return StrictImportResult(records=records, malformed_lines=[])
