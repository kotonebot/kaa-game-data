from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kaa_data import __version__
from kaa_data.config import PipelineConfig
from kaa_data.pipeline import (
    diff_backends,
    run_build,
    run_package,
    run_release,
    run_schema,
    run_sprites,
    run_tasks,
)
from kaa_data.release import gakumasu_diff_sha, prune_releases
from kaa_data.vendor import vendor_sync


def _config(root: Path | None) -> PipelineConfig:
    return PipelineConfig.load(root or Path.cwd())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kaa-data", description="Offline game data build pipeline")
    parser.add_argument("--root", type=Path, default=None, help="Project root (default: cwd)")
    parser.add_argument("--force", action="store_true", help="Force rebuild / release")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    optional = argparse.ArgumentParser(add_help=False)
    optional.add_argument("--force", action="store_true", help="Force rebuild / release")
    optional.add_argument(
        "--release-suffix",
        default=None,
        help="Release tag/manifest suffix for force builds (default: r<run_number> or timestamp)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("vendor-sync", help="Initialize submodules and apply vendor patches")

    build_p = sub.add_parser("build", parents=[optional], help="Run full pipeline")
    build_p.add_argument("--backend", choices=["gom", "campus"], default=None)

    sub.add_parser("schema", help="Build game.db from gakumasu-diff")
    sub.add_parser("tasks", help="Build tasks.json from game.db")

    sprites_p = sub.add_parser("sprites", parents=[optional], help="Download and extract sprites")
    sprites_p.add_argument("--backend", choices=["gom", "campus"], required=True)

    sub.add_parser("package", help="Compress and archive release artifacts")
    release_p = sub.add_parser("release", parents=[optional], help="Publish GitHub release")
    release_p.add_argument("--draft", action="store_true", help="Publish as draft release")
    prune_p = sub.add_parser("prune-releases", help="Delete old releases, keeping only the newest few")
    prune_p.add_argument("--keep", type=int, default=3, help="Number of newest releases to keep (default: 3)")
    prune_p.add_argument("--dry", action="store_true", help="Only list releases to remove/keep, do not delete")
    sub.add_parser("diff-backends", help="Compare gom vs campus sprite outputs")

    args = parser.parse_args(argv)
    config = _config(args.root)

    try:
        if args.command == "vendor-sync":
            vendor_sync(config.root)
        elif args.command == "schema":
            run_schema(config)
        elif args.command == "tasks":
            run_tasks(config)
        elif args.command == "sprites":
            report = run_sprites(config, args.backend, force=args.force)
            print(
                f"Sprites done: {report.tasks_ok}/{report.tasks_total} ok, "
                f"{len(report.tasks_failed)} failed, {len(report.skipped)} skipped"
            )
        elif args.command == "package":
            sha = gakumasu_diff_sha(config.gakumasu_diff)
            run_package(config, sha)
        elif args.command == "build":
            backend = args.backend or config.default_backend
            report = run_build(
                config,
                backend,
                force=args.force,
                release_suffix=args.release_suffix,
            )
            print(
                f"Build done ({backend}): {report.tasks_ok}/{report.tasks_total} ok, "
                f"{len(report.tasks_failed)} failed, {len(report.skipped)} skipped"
            )
        elif args.command == "release":
            try:
                run_release(
                    config,
                    force=args.force,
                    release_suffix=args.release_suffix,
                    draft=args.draft,
                )
            except Exception as exc:
                print(f"warning: release failed (non-fatal): {exc}", file=sys.stderr)
        elif args.command == "prune-releases":
            try:
                kept, removed = prune_releases(keep=args.keep, dry=args.dry)
            except Exception as exc:
                print(f"warning: prune-releases failed (non-fatal): {exc}", file=sys.stderr)
            else:
                print("Keep releases:")
                for tag in kept:
                    print(f"  {tag}")
                print("Remove releases:")
                for tag in removed:
                    print(f"  {tag}")
                if args.dry:
                    print("Dry run: nothing deleted")
                else:
                    print(f"Deleted {len(removed)} release(s)")
        elif args.command == "diff-backends":
            diff_backends(config)
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())