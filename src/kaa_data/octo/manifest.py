from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AssetEntry:
    name: str
    object_name: str
    md5: str
    size: int
    url_template: str

    @property
    def url(self) -> str:
        return self.url_template.replace("{o}", self.object_name)


class OctoManifest:
    def __init__(self, revision: int, url_format: str, entries: dict[str, AssetEntry]):
        self.revision = revision
        self.url_format = url_format
        self.entries = entries

    def get(self, name: str) -> AssetEntry | None:
        return self.entries.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self.entries


def _import_gom(gom_root: Path):
    root = gom_root.resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import GkmasObjectManager as gom  # type: ignore

    return gom


def fetch_manifest(gom_root: Path, *, base_revision: int = 0, request_timeout: int = 100) -> OctoManifest:
    gom = _import_gom(gom_root)

    # Apply timeout patch at runtime if vendor tree is pristine.
    utils = sys.modules.get("GkmasObjectManager.utils")
    if utils is not None:
        utils.REQUEST_TIMEOUT = request_timeout

    manifest = gom.fetch(base_revision=base_revision)
    entries: dict[str, AssetEntry] = {}

    for ab in manifest.assetbundles:
        info = ab.canon_repr
        name = info["name"]
        entries[name] = AssetEntry(
            name=name,
            object_name=info["objectName"],
            md5=info["md5"],
            size=info["size"],
            url_template=manifest.urlformat,
        )

    for res in manifest.resources:
        info = res.canon_repr
        name = info["name"]
        entries[name] = AssetEntry(
            name=name,
            object_name=info["objectName"],
            md5=info["md5"],
            size=info["size"],
            url_template=manifest.urlformat,
        )

    return OctoManifest(
        revision=manifest.version.this.rev,
        url_format=manifest.urlformat,
        entries=entries,
    )


def load_revision_state(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return 0


def save_revision_state(path: Path, revision: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(revision), encoding="utf-8")