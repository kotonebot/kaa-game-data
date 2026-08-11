from __future__ import annotations

from pathlib import Path

import UnityPy  # type: ignore
import UnityPy.config  # type: ignore

# Gakumas strips the Unity version from bundles ("0.0.0") and has migrated to
# Unity 6; the fallback must be >= 2023.2.0.18 or Texture2D fields misalign.
UnityPy.config.FALLBACK_UNITY_VERSION = "6000.0.23f1"

UNITY_SIGNATURE = b"Unity"


def extract_texture2d_png(ab_bytes: bytes, out_path: Path) -> bool:
    if not ab_bytes.startswith(UNITY_SIGNATURE):
        return False

    env = UnityPy.load(ab_bytes)
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            data.image.save(out_path)
            return True
    return False


def extract_texture2d_from_file(ab_path: Path, out_path: Path) -> bool:
    if not ab_path.exists():
        return False
    try:
        return extract_texture2d_png(ab_path.read_bytes(), out_path)
    except Exception:
        return False