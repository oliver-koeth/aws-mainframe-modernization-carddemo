"""Shared typed models for the Phase 0 backend scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict


STORE_SCHEMA_NAME = "carddemo.store"
STORE_SCHEMA_VERSION = 1
SUPPORTED_STORE_SCHEMA_VERSIONS = frozenset({STORE_SCHEMA_VERSION})
STORE_COLLECTION_NAMES = (
    "users",
    "customers",
    "accounts",
    "cards",
    "card_account_xref",
    "transaction_types",
    "transaction_categories",
    "disclosure_groups",
    "category_balances",
    "transactions",
    "report_requests",
)
STORE_OPERATION_COLLECTION_NAMES = (
    "sessions",
    "job_runs",
    "job_run_details",
)


class StoreMetadata(TypedDict):
    """Schema metadata persisted at the top of the application store."""

    schema_name: str
    schema_version: int


class StoreOperationalCollections(TypedDict):
    """Operational collections reserved for later batch and session slices."""

    sessions: list[dict[str, object]]
    job_runs: list[dict[str, object]]
    job_run_details: list[dict[str, object]]


class StoreDocument(TypedDict):
    """Canonical top-level JSON contract for `store.json`."""

    metadata: StoreMetadata
    users: list[dict[str, object]]
    customers: list[dict[str, object]]
    accounts: list[dict[str, object]]
    cards: list[dict[str, object]]
    card_account_xref: list[dict[str, object]]
    transaction_types: list[dict[str, object]]
    transaction_categories: list[dict[str, object]]
    disclosure_groups: list[dict[str, object]]
    category_balances: list[dict[str, object]]
    transactions: list[dict[str, object]]
    report_requests: list[dict[str, object]]
    operations: StoreOperationalCollections


def default_store_document() -> StoreDocument:
    """Return the empty canonical store envelope for a fresh workspace."""
    return {
        "metadata": {
            "schema_name": STORE_SCHEMA_NAME,
            "schema_version": STORE_SCHEMA_VERSION,
        },
        "users": [],
        "customers": [],
        "accounts": [],
        "cards": [],
        "card_account_xref": [],
        "transaction_types": [],
        "transaction_categories": [],
        "disclosure_groups": [],
        "category_balances": [],
        "transactions": [],
        "report_requests": [],
        "operations": {
            "sessions": [],
            "job_runs": [],
            "job_run_details": [],
        },
    }


@dataclass(slots=True)
class StoragePaths:
    """Filesystem locations for the scaffold JSON stores."""

    store: Path
    schedules: Path


@dataclass(slots=True)
class BackendState:
    """Mutable in-memory state for scaffold services."""

    paths: StoragePaths
    jobs: list[str] = field(default_factory=list)
