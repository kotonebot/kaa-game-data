from unittest import mock

from kaa_data.release.publish import list_releases, prune_releases

_SHA = "a" * 40


def _tags(count: int) -> list[str]:
    """Build `count` data-* release tags, newest first."""
    return [f"data-{_SHA}-r{i}" for i in range(count, 0, -1)]


def _fake_run(stdout: str, *, returncode: int = 0) -> mock.Mock:
    return mock.Mock(returncode=returncode, stdout=stdout, stderr="")


def test_list_releases_returns_tags_newest_first():
    with mock.patch("kaa_data.release.publish.subprocess.run") as run:
        run.return_value = _fake_run("data-1\nunrelated\ndata-2\n")
        assert list_releases() == ["data-1", "unrelated", "data-2"]


def test_list_releases_raises_on_gh_failure():
    with mock.patch("kaa_data.release.publish.subprocess.run") as run:
        run.return_value = _fake_run("", returncode=1)
        try:
            list_releases()
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected RuntimeError on gh failure")


def test_prune_releases_dry_run_only_lists():
    tags = _tags(5) + ["manual-release"]
    with mock.patch("kaa_data.release.publish.subprocess.run") as run:
        run.return_value = _fake_run("\n".join(tags) + "\n")
        kept, removed = prune_releases(keep=3, dry=True)

    assert kept == tags[:3]
    assert removed == tags[3:5]
    for call in run.call_args_list:
        assert call.args[0][:3] != ["gh", "release", "delete"]


def test_prune_releases_deletes_oldest_data_releases():
    tags = _tags(5)
    with mock.patch("kaa_data.release.publish.subprocess.run") as run:
        run.return_value = _fake_run("\n".join(tags) + "\n")
        kept, removed = prune_releases(keep=3)

    assert kept == tags[:3]
    assert removed == tags[3:]
    delete_calls = [
        call.args[0]
        for call in run.call_args_list
        if call.args[0][:3] == ["gh", "release", "delete"]
    ]
    assert delete_calls == [
        ["gh", "release", "delete", tags[3], "--yes", "--cleanup-tag"],
        ["gh", "release", "delete", tags[4], "--yes", "--cleanup-tag"],
    ]


def test_prune_releases_ignores_non_data_tags():
    with mock.patch("kaa_data.release.publish.subprocess.run") as run:
        run.return_value = _fake_run("manual\n" + "\n".join(_tags(4)) + "\n")
        kept, removed = prune_releases(keep=3, dry=True)

    assert "manual" not in kept
    assert "manual" not in removed
    assert removed == _tags(4)[3:]


def test_prune_releases_keeps_at_least_one():
    with mock.patch("kaa_data.release.publish.subprocess.run") as run:
        run.return_value = _fake_run("\n".join(_tags(2)) + "\n")
        kept, removed = prune_releases(keep=1, dry=True)

    assert kept == _tags(2)[:1]
    assert removed == _tags(2)[1:]
