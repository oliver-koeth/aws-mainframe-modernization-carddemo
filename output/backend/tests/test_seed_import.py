from __future__ import annotations

from datetime import date
from pathlib import Path

from app.models import default_store_document
from app.seed_import import (
    REPORT_REQUESTS_FILENAME,
    SEED_SOURCES,
    SeedReferentialIntegrityError,
    bootstrap_store,
    default_runtime_data_directory,
    main,
)
from app.storage import read_store


def test_bootstrap_store_populates_store_from_repo_seed_data(
    storage_paths,
) -> None:
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=seed_dir,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )
    persisted = read_store(storage_paths)

    assert persisted == payload
    assert payload["metadata"] == default_store_document()["metadata"]
    assert payload["operations"] == default_store_document()["operations"]

    for seed_source in SEED_SOURCES:
        source_lines = (seed_dir / seed_source.filename).read_text(encoding="utf-8").splitlines()
        assert len(payload[seed_source.collection_name]) == len(source_lines)

    runtime_lines = (runtime_data_dir / REPORT_REQUESTS_FILENAME).read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(payload["report_requests"]) == len(runtime_lines)


def test_seed_import_main_supports_explicit_paths(
    capsys,
    schedules_path,
    store_path,
) -> None:
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
    runtime_data_dir = default_runtime_data_directory()

    exit_code = main(
        [
            "--seed-dir",
            str(seed_dir),
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
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=seed_dir,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert len(payload["customers"]) == 50
    assert len(payload["accounts"]) == 50
    assert len(payload["cards"]) == 50
    assert len(payload["card_account_xref"]) == 50

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
    source_seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
    runtime_data_dir = default_runtime_data_directory()
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()

    for seed_source in SEED_SOURCES:
        (seed_dir / seed_source.filename).write_text(
            (source_seed_dir / seed_source.filename).read_text(encoding="utf-8"),
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
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
    runtime_data_dir = default_runtime_data_directory()

    payload = bootstrap_store(
        seed_dir=seed_dir,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert len(payload["transaction_types"]) == 7
    assert len(payload["transaction_categories"]) == 18
    assert len(payload["disclosure_groups"]) == 51
    assert len(payload["category_balances"]) == 50
    assert len(payload["report_requests"]) == 1

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


def test_bootstrap_store_treats_missing_report_request_log_as_empty(
    storage_paths,
    tmp_path,
) -> None:
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
    runtime_data_dir = tmp_path / "runtime"
    runtime_data_dir.mkdir()

    payload = bootstrap_store(
        seed_dir=seed_dir,
        runtime_data_dir=runtime_data_dir,
        storage_paths=storage_paths,
    )

    assert payload["report_requests"] == []


def test_bootstrap_store_rejects_reference_rows_with_missing_transaction_category(
    storage_paths,
    tmp_path,
) -> None:
    source_seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
    runtime_data_dir = default_runtime_data_directory()
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()

    for seed_source in SEED_SOURCES:
        (seed_dir / seed_source.filename).write_text(
            (source_seed_dir / seed_source.filename).read_text(encoding="utf-8"),
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
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"
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
            seed_dir=seed_dir,
            runtime_data_dir=runtime_data_dir,
            storage_paths=storage_paths,
        )
    except SeedReferentialIntegrityError as error:
        assert "report_requests references missing requested_by_user_id 'UNKNOWN1'" in str(
            error
        )
    else:
        raise AssertionError("Expected seed bootstrap to reject unknown report-request users")
