from __future__ import annotations

from pathlib import Path

from app.models import default_store_document
from app.seed_import import SEED_SOURCES, bootstrap_store, main
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
