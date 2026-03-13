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


def bootstrap_store(*, seed_dir: Path, storage_paths: StoragePaths) -> StoreDocument:
    """Import shipped seed data into the canonical `store.json` envelope."""
    payload = default_store_document()

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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the canonical seed bootstrap command."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    store = bootstrap_store(
        seed_dir=args.seed_dir.resolve(),
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


if __name__ == "__main__":
    raise SystemExit(main())
