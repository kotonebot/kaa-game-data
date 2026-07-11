import os
from unittest import mock

from kaa_data.release.versioning import (
    base_sha_from_tag,
    format_data_tag,
    format_manifest_version,
    parse_data_tag,
    resolve_release_suffix,
)

_SHA = "a" * 40


def test_parse_data_tag_without_suffix():
    assert parse_data_tag(f"data-{_SHA}") == (_SHA, None)


def test_parse_data_tag_with_suffix():
    assert parse_data_tag(f"data-{_SHA}-r42") == (_SHA, "r42")


def test_base_sha_from_tag_ignores_suffix():
    assert base_sha_from_tag(f"data-{_SHA}-r42") == _SHA


def test_format_data_tag_and_manifest_version():
    assert format_data_tag(_SHA) == f"data-{_SHA}"
    assert format_data_tag(_SHA, "r42") == f"data-{_SHA}-r42"
    assert format_manifest_version(_SHA) == _SHA
    assert format_manifest_version(_SHA, "r42") == f"{_SHA}-r42"


def test_resolve_release_suffix_only_when_force():
    assert resolve_release_suffix(force=False, explicit="r1") is None


def test_resolve_release_suffix_prefers_explicit():
    assert resolve_release_suffix(force=True, explicit="manual") == "manual"


def test_resolve_release_suffix_uses_env():
    with mock.patch.dict(os.environ, {"KAA_RELEASE_SUFFIX": "r99"}, clear=False):
        assert resolve_release_suffix(force=True) == "r99"


def test_resolve_release_suffix_uses_github_run_number():
    env = {"GITHUB_RUN_NUMBER": "17"}
    with mock.patch.dict(os.environ, env, clear=True):
        assert resolve_release_suffix(force=True) == "r17"