from __future__ import annotations

from pathlib import Path

from app.models import default_store_document
from app.seed_import import (
    SEED_SOURCES,
    SeedReferentialIntegrityError,
    bootstrap_store,
    main,
)
from app.storage import read_store


def test_bootstrap_store_populates_store_from_repo_seed_data(
    storage_paths,
) -> None:
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"

    payload = bootstrap_store(seed_dir=seed_dir, storage_paths=storage_paths)
    persisted = read_store(storage_paths)

    assert persisted == payload
    assert payload["metadata"] == default_store_document()["metadata"]
    assert payload["report_requests"] == []
    assert payload["operations"] == default_store_document()["operations"]

    for seed_source in SEED_SOURCES:
        source_lines = (seed_dir / seed_source.filename).read_text(encoding="utf-8").splitlines()
        assert len(payload[seed_source.collection_name]) == len(source_lines)


def test_seed_import_main_supports_explicit_paths(
    capsys,
    schedules_path,
    store_path,
) -> None:
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"

    exit_code = main(
        [
            "--seed-dir",
            str(seed_dir),
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
    assert store_path.exists()


def test_bootstrap_store_preserves_identity_account_relationships(
    storage_paths,
) -> None:
    seed_dir = Path(__file__).resolve().parents[3] / "app" / "data" / "ASCII.seed"

    payload = bootstrap_store(seed_dir=seed_dir, storage_paths=storage_paths)

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
        bootstrap_store(seed_dir=seed_dir, storage_paths=storage_paths)
    except SeedReferentialIntegrityError as error:
        assert "card_account_xref references missing account_id '99999999999'" in str(error)
    else:
        raise AssertionError("Expected seed bootstrap to reject mismatched card/account xref")
