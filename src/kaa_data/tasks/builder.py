from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from kaa_data.models import AssetTask, TaskManifest

CHARACTER_IDS = [
    "hski", "ttmr", "fktn", "amao", "kllj",
    "kcna", "ssmk", "shro", "hrnm", "hume",
    "jsna", "atbm",
]


def build_tasks(database: Path, sprites_dir: Path) -> TaskManifest:
    if not database.exists():
        raise FileNotFoundError(f"game.db not found: {database}")

    manifest = TaskManifest(sprites_dir=sprites_dir)
    db = sqlite3.connect(database)

    try:
        _add_idol_card_tasks(db, manifest)
        _add_skill_card_tasks(db, manifest)
        _add_drink_tasks(db, manifest)
    finally:
        db.close()

    return manifest


def _add_idol_card_tasks(db: sqlite3.Connection, manifest: TaskManifest) -> None:
    cur = db.execute(
        """
        SELECT ICS.id AS skinId, ICS.assetId, IC.primaStellaConsumptionSetId
        FROM IdolCardSkin ICS
        LEFT JOIN IdolCard IC ON ICS.idolCardId = IC.id
        WHERE ICS.assetId IS NOT NULL
        """
    )
    for skin_id, asset_id, prima_stella_id in cur.fetchall():
        for variant in ("0", "1"):
            manifest.tasks.append(
                AssetTask(
                    asset_name=f"img_general_{asset_id}_{variant}-thumb-portrait",
                    output_path=manifest.sprites_dir / f"idol_cards/{skin_id}_{variant}.png",
                    ref_id=skin_id,
                    post_process="resizeIdolCard",
                    expected_size=(140, 188),
                )
            )
        # `_2` 变体仅存在于带 Prima Stella（一番星）形态的卡，由
        # IdolCard.primaStellaConsumptionSetId 非空标识。
        if prima_stella_id:
            manifest.tasks.append(
                AssetTask(
                    asset_name=f"img_general_{asset_id}_2-thumb-portrait",
                    output_path=manifest.sprites_dir / f"idol_cards/{skin_id}_2.png",
                    ref_id=skin_id,
                    post_process="resizeIdolCard",
                    expected_size=(140, 188),
                )
            )


def _add_skill_card_tasks(db: sqlite3.Connection, manifest: TaskManifest) -> None:
    cur = db.execute(
        """
        SELECT DISTINCT assetId, isCharacterAsset
        FROM ProduceCard
        WHERE assetId IS NOT NULL
        """
    )
    for asset_id, is_char in cur.fetchall():
        if not is_char:
            manifest.tasks.append(
                AssetTask(
                    asset_name=asset_id,
                    output_path=manifest.sprites_dir / f"skill_cards/{asset_id}.png",
                    ref_id=asset_id,
                )
            )
        else:
            for cid in CHARACTER_IDS:
                full_aid = f"{asset_id}-{cid}"
                manifest.tasks.append(
                    AssetTask(
                        asset_name=full_aid,
                        output_path=manifest.sprites_dir / f"skill_cards/{full_aid}.png",
                        ref_id=full_aid,
                    )
                )


def _add_drink_tasks(db: sqlite3.Connection, manifest: TaskManifest) -> None:
    cur = db.execute(
        """
        SELECT DISTINCT assetId
        FROM ProduceDrink
        WHERE assetId IS NOT NULL
        """
    )
    for (asset_id,) in cur.fetchall():
        manifest.tasks.append(
            AssetTask(
                asset_name=asset_id,
                output_path=manifest.sprites_dir / f"drinks/{asset_id}.png",
                ref_id=asset_id,
                post_process="resizeDrink",
                expected_size=(68, 68),
            )
        )


def write_tasks(manifest: TaskManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_json(), f, ensure_ascii=False, indent=2)


def read_tasks(path: Path) -> TaskManifest:
    with path.open(encoding="utf-8") as f:
        return TaskManifest.from_json(json.load(f))