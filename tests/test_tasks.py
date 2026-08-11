import sqlite3
from pathlib import Path

from kaa_data.models import TaskManifest
from kaa_data.tasks.builder import build_tasks


def test_build_tasks_from_minimal_db(tmp_path: Path):
    db_path = tmp_path / "game.db"
    sprites_dir = tmp_path / "sprites"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IdolCard (id TEXT, assetId TEXT, primaStellaConsumptionSetId TEXT);
        CREATE TABLE IdolCardSkin (id TEXT, idolCardId TEXT, assetId TEXT);
        CREATE TABLE ProduceCard (assetId TEXT, isCharacterAsset INTEGER);
        CREATE TABLE ProduceDrink (assetId TEXT);
        INSERT INTO IdolCard VALUES ('i_card-hski-3-001', 'cidol-hski-3-001', NULL);
        INSERT INTO IdolCardSkin VALUES ('skin-1', 'i_card-hski-3-001', 'cidol-hski-3-001');
        """
    )
    conn.commit()
    conn.close()

    manifest = build_tasks(db_path, sprites_dir)
    assert len(manifest.tasks) == 2
    assert manifest.tasks[0].asset_name.endswith("-thumb-portrait")

    payload = manifest.to_json()
    restored = TaskManifest.from_json(payload)
    assert restored.tasks[0].output_path == manifest.tasks[0].output_path


def test_build_tasks_adds_prima_stella_variant(tmp_path: Path):
    db_path = tmp_path / "game.db"
    sprites_dir = tmp_path / "sprites"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IdolCard (id TEXT, assetId TEXT, primaStellaConsumptionSetId TEXT);
        CREATE TABLE IdolCardSkin (id TEXT, idolCardId TEXT, assetId TEXT);
        CREATE TABLE ProduceCard (assetId TEXT, isCharacterAsset INTEGER);
        CREATE TABLE ProduceDrink (assetId TEXT);
        INSERT INTO IdolCard VALUES (
            'i_card-amao-3-015', 'cidol-amao-3-015',
            'cs-idol_card_prima_stella-i_card-amao-3-015'
        );
        INSERT INTO IdolCardSkin VALUES (
            'skin-ps', 'i_card-amao-3-015', 'cidol-amao-3-015'
        );
        """
    )
    conn.commit()
    conn.close()

    manifest = build_tasks(db_path, sprites_dir)
    names = [t.asset_name for t in manifest.tasks]
    assert len(manifest.tasks) == 3
    assert "img_general_cidol-amao-3-015_2-thumb-portrait" in names