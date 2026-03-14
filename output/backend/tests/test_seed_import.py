from __future__ import annotations

from datetime import date
from pathlib import Path

from app.models import (
    STORE_COLLECTION_NAMES,
    STORE_OPERATION_COLLECTION_NAMES,
    default_store_document,
)
from app.seed_import import (
    REPORT_REQUESTS_FILENAME,
    SEED_SOURCES,
    SeedReferentialIntegrityError,
    bootstrap_store,
    default_runtime_data_directory,
    main,
    summarize_store_counts,
)
from app.services import build_backend_state
from app.storage import read_store


REPO_SEED_DIR = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
BASELINE_IMPORT_COUNTS = {
    "users": 2,
    "customers": 50,
    "accounts": 50,
    "cards": 50,
    "card_account_xref": 50,
    "transaction_types": 7,
    "transaction_categories": 18,
    "disclosure_groups": 51,
    "category_balances": 50,
    "transactions": 300,
    "report_requests": 1,
    "operations.sessions": 0,
    "operations.job_runs": 0,
    "operations.job_run_details": 0,
}


def assert_baseline_import_counts(payload) -> None:
    assert len(payload["users"]) == BASELINE_IMPORT_COUNTS["users"]
    assert len(payload["customers"]) == BASELINE_IMPORT_COUNTS["customers"]
    assert len(payload["accounts"]) == BASELINE_IMPORT_COUNTS["accounts"]
    assert len(payload["cards"]) == BASELINE_IMPORT_COUNTS["cards"]
    assert len(payload["card_account_xref"]) == BASELINE_IMPORT_COUNTS["card_account_xref"]
    assert len(payload["transaction_types"]) == BASELINE_IMPORT_COUNTS["transaction_types"]
    assert len(payload["transaction_categories"]) == BASELINE_IMPORT_COUNTS[
        "transaction_categories"
    ]
    assert len(payload["disclosure_groups"]) == BASELINE_IMPORT_COUNTS["disclosure_groups"]
    assert len(payload["category_balances"]) == BASELINE_IMPORT_COUNTS["category_balances"]
    assert len(payload["transactions"]) == BASELINE_IMPORT_COUNTS["transactions"]
    assert len(payload["report_requests"]) == BASELINE_IMPORT_COUNTS["report_requests"]
    assert len(payload["operations"]["sessions"]) == BASELINE_IMPORT_COUNTS["operations.sessions"]
    assert len(payload["operations"]["job_runs"]) == BASELINE_IMPORT_COUNTS[
        "operations.job_runs"
    ]
    assert len(payload["operations"]["job_run_details"]) == BASELINE_IMPORT_COUNTS[
        "operations.job_run_details"
    ]


def test_bootstrap_store_populates_store_from_repo_seed_data(
    storage_paths,
) -> None:
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=REPO_SEED_DIR,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )
    persisted = read_store(storage_paths)

    assert persisted == payload
    assert payload["metadata"] == default_store_document()["metadata"]
    assert payload["operations"] == default_store_document()["operations"]

    for seed_source in SEED_SOURCES:
        source_lines = (REPO_SEED_DIR / seed_source.filename).read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(payload[seed_source.collection_name]) == len(source_lines)

    runtime_lines = (runtime_data_dir / REPORT_REQUESTS_FILENAME).read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(payload["report_requests"]) == len(runtime_lines)


def test_bootstrap_store_preserves_complete_store_envelope(
    storage_paths,
) -> None:
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=REPO_SEED_DIR,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert set(payload) == {
        "metadata",
        *STORE_COLLECTION_NAMES,
        "operations",
    }
    assert payload["metadata"] == default_store_document()["metadata"]
    for collection_name in STORE_COLLECTION_NAMES:
        assert isinstance(payload[collection_name], list)

    assert set(payload["operations"]) == set(STORE_OPERATION_COLLECTION_NAMES)
    for collection_name in STORE_OPERATION_COLLECTION_NAMES:
        assert payload["operations"][collection_name] == []


def test_imported_store_loads_from_backend_state_without_manual_edits(
    tmp_path,
) -> None:
    runtime_data_dir = default_runtime_data_directory()
    backend_root = tmp_path / "backend"
    backend_root.mkdir()
    state = build_backend_state(backend_root)

    payload = bootstrap_store(
        seed_dir=REPO_SEED_DIR,
        runtime_data_dir=runtime_data_dir,
        storage_paths=state.paths,
    )

    assert read_store(state.paths) == payload
    assert state.paths.store.exists()
    assert not state.paths.schedules.exists()


def test_seed_import_main_supports_explicit_paths(
    capsys,
    schedules_path,
    store_path,
) -> None:
    runtime_data_dir = default_runtime_data_directory()

    exit_code = main(
        [
            "--seed-dir",
            str(REPO_SEED_DIR),
            "--runtime-data-dir",
            str(runtime_data_dir),
            "--store-path",
            str(store_path),
            "--schedules-path",
            str(schedules_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Initialized" in captured.out
    assert str(store_path.resolve()) in captured.out
    assert "users=2" in captured.out
    assert "report_requests=1" in captured.out
    assert store_path.exists()


def test_bootstrap_store_preserves_identity_account_relationships(
    storage_paths,
) -> None:
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=REPO_SEED_DIR,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert_baseline_import_counts(payload)

    customer_ids = {record["customer_id"] for record in payload["customers"]}
    account_ids = {record["account_id"] for record in payload["accounts"]}
    cards_by_number = {
        record["card_number"]: record for record in payload["cards"]
    }

    assert len(customer_ids) == len(payload["customers"])
    assert len(account_ids) == len(payload["accounts"])
    assert len(cards_by_number) == len(payload["cards"])

    for record in payload["cards"]:
        assert record["account_id"] in account_ids

    for record in payload["card_account_xref"]:
        assert record["customer_id"] in customer_ids
        assert record["account_id"] in account_ids
        assert record["card_number"] in cards_by_number
        assert cards_by_number[record["card_number"]]["account_id"] == record["account_id"]


def test_bootstrap_store_rejects_card_xref_account_mismatch(
    storage_paths,
    tmp_path,
) -> None:
    runtime_data_dir = default_runtime_data_directory()
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()

    for seed_source in SEED_SOURCES:
        (seed_dir / seed_source.filename).write_text(
            (REPO_SEED_DIR / seed_source.filename).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    cardxref_path = seed_dir / "cardxref.txt"
    lines = cardxref_path.read_text(encoding="utf-8").splitlines()
    assert lines
    lines[0] = f"{lines[0][:25]}99999999999{lines[0][36:]}"
    cardxref_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    try:
        bootstrap_store(
            seed_dir=seed_dir,
            runtime_data_dir=runtime_data_dir,
            storage_paths=storage_paths,
        )
    except SeedReferentialIntegrityError as error:
        assert "card_account_xref references missing account_id '99999999999'" in str(error)
    else:
        raise AssertionError("Expected seed bootstrap to reject mismatched card/account xref")


def test_bootstrap_store_imports_reference_data_and_report_requests(
    storage_paths,
) -> None:
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=REPO_SEED_DIR,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert_baseline_import_counts(payload)

    transaction_type_codes = {
        record["transaction_type_code"] for record in payload["transaction_types"]
    }
    transaction_category_keys = {
        (record["transaction_type_code"], record["transaction_category_code"])
        for record in payload["transaction_categories"]
    }
    account_ids = {record["account_id"] for record in payload["accounts"]}
    user_ids = {record["user_id"] for record in payload["users"]}

    for record in payload["transaction_categories"]:
        assert record["transaction_type_code"] in transaction_type_codes

    for record in payload["disclosure_groups"]:
        assert (
            record["transaction_type_code"],
            record["transaction_category_code"],
        ) in transaction_category_keys

    for record in payload["category_balances"]:
        assert record["account_id"] in account_ids
        assert (
            record["transaction_type_code"],
            record["transaction_category_code"],
        ) in transaction_category_keys

    report_request = payload["report_requests"][0]
    assert report_request["requested_by_user_id"] in user_ids
    assert report_request["report_type"] == "Custom"
    assert report_request["start_date"] == date(2026, 3, 1)
    assert report_request["end_date"] == date(2026, 3, 10)


def test_bootstrap_store_matches_phase_1_baseline_snapshot(
    storage_paths,
) -> None:
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=REPO_SEED_DIR,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert_baseline_import_counts(payload)
    assert summarize_store_counts(payload) == (
        "users=2, customers=50, accounts=50, cards=50, card_account_xref=50, "
        "transaction_types=7, transaction_categories=18, disclosure_groups=51, "
        "category_balances=50, transactions=300, report_requests=1, "
        "operations.sessions=0, operations.job_runs=0, operations.job_run_details=0"
    )


def test_bootstrap_store_treats_missing_report_request_log_as_empty(
    storage_paths,
    tmp_path,
) -> None:
    runtime_data_dir = tmp_path / "runtime"
    runtime_data_dir.mkdir()

    payload = bootstrap_store(
        seed_dir=REPO_SEED_DIR,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert payload["report_requests"] == []


def test_bootstrap_store_rejects_reference_rows_with_missing_transaction_category(
    storage_paths,
    tmp_path,
) -> None:
    runtime_data_dir = default_runtime_data_directory()
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()

    for seed_source in SEED_SOURCES:
        (seed_dir / seed_source.filename).write_text(
            (REPO_SEED_DIR / seed_source.filename).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    trancatg_path = seed_dir / "trancatg.txt"
    lines = trancatg_path.read_text(encoding="utf-8").splitlines()
    assert lines
    trancatg_path.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")

    try:
        bootstrap_store(
            seed_dir=seed_dir,
            runtime_data_dir=runtime_data_dir,
            storage_paths=storage_paths,
        )
    except SeedReferentialIntegrityError as error:
        assert "category_balances references missing transaction category" in str(error)
    else:
        raise AssertionError(
            "Expected seed bootstrap to reject reference rows with missing categories"
        )


def test_bootstrap_store_rejects_report_request_for_unknown_user(
    storage_paths,
    tmp_path,
) -> None:
    source_runtime_dir = default_runtime_data_directory()
    runtime_data_dir = tmp_path / "runtime"
    runtime_data_dir.mkdir()
    report_requests_path = runtime_data_dir / REPORT_REQUESTS_FILENAME
    report_requests_path.write_text(
        (source_runtime_dir / REPORT_REQUESTS_FILENAME).read_text(encoding="utf-8").replace(
            "USER0001",
            "UNKNOWN1",
            1,
        ),
        encoding="utf-8",
    )

    try:
        bootstrap_store(
            seed_dir=REPO_SEED_DIR,
            runtime_data_dir=runtime_data_dir,
            storage_paths=storage_paths,
        )
    except SeedReferentialIntegrityError as error:
        assert "report_requests references missing requested_by_user_id 'UNKNOWN1'" in str(
            error
        )
    else:
        raise AssertionError("Expected seed bootstrap to reject unknown report-request users")
