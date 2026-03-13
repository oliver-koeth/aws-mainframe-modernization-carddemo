"""Canonical Phase 1 seed bootstrap entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from app.domain import (
    parse_account_record,
    parse_card_account_xref_record,
    parse_card_record,
    parse_category_balance_record,
    parse_customer_record,
    parse_disclosure_group_record,
    parse_report_request_record,
    parse_transaction_category_record,
    parse_transaction_record,
    parse_transaction_type_record,
    parse_user_security_record,
)
from app.importing import LineParser, parse_lines_strict
from app.models import StoragePaths, StoreDocument, default_store_document
from app.storage import write_store


@dataclass(slots=True, frozen=True)
class SeedSource:
    """One fixed-width seed file and its target store collection."""

    collection_name: str
    filename: str
    parser: LineParser[BaseModel]


class SeedReferentialIntegrityError(ValueError):
    """Raised when individually valid seed rows fail required cross-file joins."""


SEED_SOURCES: tuple[SeedSource, ...] = (
    SeedSource("users", "usrsec.dat", parse_user_security_record),
    SeedSource("customers", "custdata.txt", parse_customer_record),
    SeedSource("accounts", "acctdata.txt", parse_account_record),
    SeedSource("cards", "carddata.txt", parse_card_record),
    SeedSource("card_account_xref", "cardxref.txt", parse_card_account_xref_record),
    SeedSource("transaction_types", "trantype.txt", parse_transaction_type_record),
    SeedSource(
        "transaction_categories",
        "trancatg.txt",
        parse_transaction_category_record,
    ),
    SeedSource("disclosure_groups", "discgrp.txt", parse_disclosure_group_record),
    SeedSource("category_balances", "tcatbal.txt", parse_category_balance_record),
    SeedSource("transactions", "dailytran.txt", parse_transaction_record),
)
REPORT_REQUESTS_FILENAME = "tranrept_requests.txt"


def bootstrap_store(
    *,
    seed_dir: Path,
    runtime_data_dir: Path | None = None,
    storage_paths: StoragePaths,
) -> StoreDocument:
    """Import shipped seed data into the canonical `store.json` envelope."""
    payload = default_store_document()
    runtime_source_dir = runtime_data_dir or default_runtime_data_directory()

    for seed_source in SEED_SOURCES:
        records = _parse_seed_file(
            seed_dir / seed_source.filename,
            parser=seed_source.parser,
        )
        _set_store_collection(
            payload,
            seed_source.collection_name,
            records,
        )

    report_requests = _parse_runtime_file(
        runtime_source_dir / REPORT_REQUESTS_FILENAME,
        parser=parse_report_request_record,
        missing_means_empty=True,
    )
    _set_store_collection(payload, "report_requests", report_requests)

    validate_identity_account_seed_relationships(payload)
    validate_transaction_reference_seed_relationships(payload)
    write_store(storage_paths, payload)
    return payload


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the canonical seed bootstrap command."""
    backend_root = default_backend_root()
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap output/backend/store.json from the shipped "
            "app/data/ASCII.seed files."
        )
    )
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=default_seed_directory(),
        help="Directory containing the shipped GNUCobol seed flat files.",
    )
    parser.add_argument(
        "--store-path",
        type=Path,
        default=backend_root / "store.json",
        help="Target store.json path to initialize.",
    )
    parser.add_argument(
        "--schedules-path",
        type=Path,
        default=backend_root / "schedules.json",
        help="Companion schedules.json path for storage wiring.",
    )
    parser.add_argument(
        "--runtime-data-dir",
        type=Path,
        default=default_runtime_data_directory(),
        help="Directory containing runtime-managed files such as tranrept_requests.txt.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the canonical seed bootstrap command."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    store = bootstrap_store(
        seed_dir=args.seed_dir.resolve(),
        runtime_data_dir=args.runtime_data_dir.resolve(),
        storage_paths=StoragePaths(
            store=args.store_path.resolve(),
            schedules=args.schedules_path.resolve(),
        ),
    )
    print(
        "Initialized "
        f"{args.store_path.resolve()} from {args.seed_dir.resolve()} "
        f"with {summarize_store_counts(store)}"
    )
    return 0


def summarize_store_counts(store: StoreDocument) -> str:
    """Render the imported store collection counts for CLI output."""
    summaries = [
        f"{seed_source.collection_name}="
        f"{len(_get_store_collection(store, seed_source.collection_name))}"
        for seed_source in SEED_SOURCES
    ]
    summaries.extend(
        (
            f"report_requests={len(store['report_requests'])}",
            f"operations.sessions={len(store['operations']['sessions'])}",
            f"operations.job_runs={len(store['operations']['job_runs'])}",
            f"operations.job_run_details={len(store['operations']['job_run_details'])}",
        )
    )
    return ", ".join(summaries)


def default_backend_root() -> Path:
    """Resolve the backend workspace root from this module location."""
    return Path(__file__).resolve().parents[1]


def default_seed_directory() -> Path:
    """Resolve the shipped seed directory relative to the repository root."""
    return repository_root() / "app" / "data" / "ASCII.seed"


def default_runtime_data_directory() -> Path:
    """Resolve the GNUCobol runtime data directory relative to the repository root."""
    return repository_root() / "app" / "data" / "ASCII"


def repository_root() -> Path:
    """Resolve the repository root from this module location."""
    return Path(__file__).resolve().parents[3]


def _parse_seed_file(path: Path, *, parser: LineParser[BaseModel]) -> list[dict[str, Any]]:
    """Read, validate, and normalize one seed file into JSON-ready records."""
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    parsed = parse_lines_strict(lines, source_name=path.name, parser=parser)
    return [record.model_dump(mode="python") for record in parsed.records]


def _parse_runtime_file(
    path: Path,
    *,
    parser: LineParser[BaseModel],
    missing_means_empty: bool = False,
) -> list[dict[str, Any]]:
    """Read one runtime-managed file into JSON-ready records."""
    if not path.exists():
        if missing_means_empty:
            return []
        raise FileNotFoundError(f"Runtime file not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    parsed = parse_lines_strict(lines, source_name=path.name, parser=parser)
    return [record.model_dump(mode="python") for record in parsed.records]


def _get_store_collection(
    store: StoreDocument,
    collection_name: str,
) -> list[dict[str, Any]]:
    """Access a top-level store collection with a typed list view."""
    return cast(list[dict[str, Any]], cast(dict[str, Any], store)[collection_name])


def _set_store_collection(
    store: StoreDocument,
    collection_name: str,
    records: list[dict[str, Any]],
) -> None:
    """Write a top-level store collection through one typed helper."""
    cast(dict[str, Any], store)[collection_name] = records


def validate_identity_account_seed_relationships(store: StoreDocument) -> None:
    """Fail bootstrap when customer/account/card seed relationships drift."""
    customer_ids = {
        _required_string_field(record, "customer_id", collection_name="customers")
        for record in store["customers"]
    }
    account_ids = {
        _required_string_field(record, "account_id", collection_name="accounts")
        for record in store["accounts"]
    }
    cards_by_number = {
        _required_string_field(record, "card_number", collection_name="cards"): record
        for record in store["cards"]
    }

    for record in store["cards"]:
        account_id = _required_string_field(record, "account_id", collection_name="cards")
        card_number = _required_string_field(record, "card_number", collection_name="cards")
        if account_id not in account_ids:
            raise SeedReferentialIntegrityError(
                "cards references missing account_id "
                f"{account_id!r} for card_number {card_number!r}."
            )

    for record in store["card_account_xref"]:
        card_number = _required_string_field(
            record,
            "card_number",
            collection_name="card_account_xref",
        )
        customer_id = _required_string_field(
            record,
            "customer_id",
            collection_name="card_account_xref",
        )
        account_id = _required_string_field(
            record,
            "account_id",
            collection_name="card_account_xref",
        )
        if customer_id not in customer_ids:
            raise SeedReferentialIntegrityError(
                "card_account_xref references missing customer_id "
                f"{customer_id!r} for card_number {card_number!r}."
            )
        if account_id not in account_ids:
            raise SeedReferentialIntegrityError(
                "card_account_xref references missing account_id "
                f"{account_id!r} for card_number {card_number!r}."
            )
        card = cards_by_number.get(card_number)
        if card is None:
            raise SeedReferentialIntegrityError(
                "card_account_xref references missing card_number "
                f"{card_number!r}."
            )
        card_account_id = _required_string_field(
            card,
            "account_id",
            collection_name="cards",
        )
        if card_account_id != account_id:
            raise SeedReferentialIntegrityError(
                "card_account_xref account_id "
                f"{account_id!r} does not match cards.account_id {card_account_id!r} "
                f"for card_number {card_number!r}."
            )


def validate_transaction_reference_seed_relationships(store: StoreDocument) -> None:
    """Fail bootstrap when transaction-reference or report-request joins drift."""
    account_ids = {
        _required_string_field(record, "account_id", collection_name="accounts")
        for record in store["accounts"]
    }
    user_ids = {
        _required_string_field(record, "user_id", collection_name="users")
        for record in store["users"]
    }
    card_numbers = {
        _required_string_field(record, "card_number", collection_name="cards")
        for record in store["cards"]
    }
    transaction_type_codes = {
        _required_string_field(
            record,
            "transaction_type_code",
            collection_name="transaction_types",
        )
        for record in store["transaction_types"]
    }
    transaction_category_keys = {
        _required_composite_transaction_category_key(
            record,
            collection_name="transaction_categories",
        )
        for record in store["transaction_categories"]
    }

    for record in store["transaction_categories"]:
        transaction_type_code = _required_string_field(
            record,
            "transaction_type_code",
            collection_name="transaction_categories",
        )
        transaction_category_code = _required_string_field(
            record,
            "transaction_category_code",
            collection_name="transaction_categories",
        )
        if transaction_type_code not in transaction_type_codes:
            raise SeedReferentialIntegrityError(
                "transaction_categories references missing transaction_type_code "
                f"{transaction_type_code!r} for transaction_category_code "
                f"{transaction_category_code!r}."
            )

    for collection_name in ("category_balances", "disclosure_groups", "transactions"):
        for record in store[collection_name]:
            category_key = _required_composite_transaction_category_key(
                record,
                collection_name=collection_name,
            )
            if category_key not in transaction_category_keys:
                raise SeedReferentialIntegrityError(
                    f"{collection_name} references missing transaction category "
                    f"{category_key[0]!r}/{category_key[1]!r}."
                )

    for record in store["category_balances"]:
        account_id = _required_string_field(
            record,
            "account_id",
            collection_name="category_balances",
        )
        if account_id not in account_ids:
            raise SeedReferentialIntegrityError(
                "category_balances references missing account_id "
                f"{account_id!r}."
            )

    for record in store["transactions"]:
        card_number = _required_string_field(
            record,
            "card_number",
            collection_name="transactions",
        )
        if card_number not in card_numbers:
            raise SeedReferentialIntegrityError(
                "transactions references missing card_number "
                f"{card_number!r}."
            )

    for record in store["report_requests"]:
        requested_by_user_id = _required_string_field(
            record,
            "requested_by_user_id",
            collection_name="report_requests",
        )
        if requested_by_user_id not in user_ids:
            raise SeedReferentialIntegrityError(
                "report_requests references missing requested_by_user_id "
                f"{requested_by_user_id!r}."
            )


def _required_string_field(
    record: dict[str, object],
    field_name: str,
    *,
    collection_name: str,
) -> str:
    value = record.get(field_name)
    if not isinstance(value, str) or value == "":
        raise SeedReferentialIntegrityError(
            f"{collection_name} record is missing required string field {field_name!r}."
        )
    return value


def _required_composite_transaction_category_key(
    record: dict[str, object],
    *,
    collection_name: str,
) -> tuple[str, str]:
    return (
        _required_string_field(
            record,
            "transaction_type_code",
            collection_name=collection_name,
        ),
        _required_string_field(
            record,
            "transaction_category_code",
            collection_name=collection_name,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
