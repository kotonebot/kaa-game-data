from __future__ import annotations

import os
import re
from datetime import datetime, timezone

_DATA_TAG_RE = re.compile(r"^data-([0-9a-f]{40})(?:-(.+))?$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_data_tag(tag: str) -> tuple[str, str | None] | None:
    match = _DATA_TAG_RE.match(tag.strip())
    if match is None:
        return None
    return match.group(1), match.group(2)


def base_sha_from_tag(tag: str) -> str | None:
    parsed = parse_data_tag(tag)
    if parsed is not None:
        return parsed[0]

    rest = tag.removeprefix("data-")
    if len(rest) >= 40 and _SHA_RE.fullmatch(rest[:40]):
        return rest[:40]
    return None


def format_data_tag(sha: str, suffix: str | None = None) -> str:
    if suffix:
        return f"data-{sha}-{suffix}"
    return f"data-{sha}"


def format_manifest_version(sha: str, suffix: str | None = None) -> str:
    if suffix:
        return f"{sha}-{suffix}"
    return sha


def resolve_release_suffix(*, force: bool, explicit: str | None = None) -> str | None:
    if not force:
        return None
    if explicit and explicit.strip():
        return explicit.strip()

    env_suffix = os.environ.get("KAA_RELEASE_SUFFIX", "").strip()
    if env_suffix:
        return env_suffix

    run_number = os.environ.get("GITHUB_RUN_NUMBER", "").strip()
    if run_number:
        return f"r{run_number}"

    return datetime.now(timezone.utc).strftime("local-%Y%m%dT%H%M%SZ")