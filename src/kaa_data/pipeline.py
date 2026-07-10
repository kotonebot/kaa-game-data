from __future__ import annotations

import json
from pathlib import Path

from kaa_data.config import PipelineConfig
from kaa_data.models import FetchReport
from kaa_data.schema import build_schema
from kaa_data.tasks import build_tasks, read_tasks, write_tasks


def run_schema(config: PipelineConfig) -> None:
    config.ensure_output_dirs()
    build_schema(config.gakumasu_diff, config.game_db)


def run_tasks(config: PipelineConfig):
    config.ensure_output_dirs()
    manifest = build_tasks(config.game_db, config.sprites_dir)
    write_tasks(manifest, config.tasks_path)
    return manifest


def run_sprites(config: PipelineConfig, backend_name: str, *, force: bool = False) -> FetchReport:
    from kaa_data.backends import get_backend

    config.ensure_output_dirs()
    if config.tasks_path.exists():
        task_manifest = read_tasks(config.tasks_path)
    else:
        task_manifest = run_tasks(config)

    backend = get_backend(backend_name)
    backend.healthcheck(config)
    return backend.fetch(config, task_manifest, force=force)


def run_package(config: PipelineConfig, sha: str) -> dict:
    from kaa_data.package import build_manifest, compress_db, zip_directory

    config.ensure_output_dirs()
    release_dir = config.release_dir

    compress_db(
        config.game_db,
        release_dir / "game.db.zst",
        level=config.zstd_level,
    )
    zip_directory(config.sprites_dir / "idol_cards", release_dir / "idol_cards.zip")
    zip_directory(config.sprites_dir / "skill_cards", release_dir / "skill_cards.zip")
    zip_directory(config.sprites_dir / "drinks", release_dir / "drinks.zip")
    files = build_manifest(sha, config.game_db, config.sprites_dir, release_dir / "manifest.json")
    return files


def run_build(config: PipelineConfig, backend_name: str, *, force: bool = False) -> FetchReport:
    from kaa_data.release import gakumasu_diff_sha, make_build_report, write_build_report

    sha = gakumasu_diff_sha(config.gakumasu_diff)
    run_schema(config)
    task_manifest = run_tasks(config)
    fetch_report = run_sprites(config, backend_name, force=force)

    output_files = run_package(config, sha)
    report = make_build_report(sha, backend_name, fetch_report, output_files)
    write_build_report(config.build_report_path, report)

    skipped_path = config.output_dir / "skipped_assets.json"
    with skipped_path.open("w", encoding="utf-8") as f:
        json.dump([s.to_json() for s in fetch_report.skipped], f, ensure_ascii=False, indent=2)

    return fetch_report


def run_release(config: PipelineConfig, *, force: bool = False) -> None:
    from kaa_data.release import gakumasu_diff_sha, needs_release, publish_release

    sha = gakumasu_diff_sha(config.gakumasu_diff)
    if not needs_release(sha, force=force):
        print(f"No release needed for {sha}")
        return

    tag = f"data-{sha}"
    skipped = []
    skipped_path = config.output_dir / "skipped_assets.json"
    if skipped_path.exists():
        raw = json.loads(skipped_path.read_text(encoding="utf-8"))
        from kaa_data.models import SkippedAsset

        skipped = [SkippedAsset(x["id"], x["refId"], x.get("reason", "")) for x in raw]

    notes_path = config.root / "release_notes.md"
    extra_assets = [
        path
        for path in (config.output_dir / "skipped_assets.json", config.build_report_path)
        if path.exists()
    ]
    publish_release(tag, sha, config.release_dir, skipped, notes_path, extra_assets=extra_assets)


def diff_backends(config: PipelineConfig) -> None:
    import hashlib

    from kaa_data.backends import get_backend

    reports: dict[str, dict[str, str]] = {}
    for name in ("gom", "campus"):
        out_dir = config.output_dir / f"sprites-{name}"
        alt = PipelineConfig.load(config.root)
        alt.sprites_dir = out_dir
        alt.tasks_path = config.output_dir / f"tasks-{name}.json"
        alt.ensure_output_dirs()

        manifest = build_tasks(config.game_db, out_dir)
        write_tasks(manifest, alt.tasks_path)
        backend = get_backend(name)
        backend.healthcheck(alt)
        backend.fetch(alt, manifest)

        files: dict[str, str] = {}
        for png in out_dir.rglob("*.png"):
            rel = png.relative_to(out_dir).as_posix()
            files[rel] = hashlib.md5(png.read_bytes()).hexdigest()
        reports[name] = files

    gom_files = reports["gom"]
    campus_files = reports["campus"]
    all_keys = sorted(set(gom_files) | set(campus_files))
    diff_count = 0
    for key in all_keys:
        gom_md5 = gom_files.get(key)
        campus_md5 = campus_files.get(key)
        if gom_md5 != campus_md5:
            diff_count += 1
            print(f"DIFF {key}: gom={gom_md5} campus={campus_md5}")
    print(f"Compared {len(all_keys)} files, {diff_count} differences")