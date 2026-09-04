"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import (
    collect_context,
    default_cache_path,
    download_catalog,
    enrich_candidates,
    iter_catalog,
    rank_candidates,
    render_report,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="ate-scan",
        description="Recommend candidate MCP tools from local project metadata.",
    )
    result.add_argument("paths", nargs="+", type=Path, help="Project folders to scan")
    result.add_argument("--catalog", type=Path, help="Use a local ATE JSONL or CSV catalog")
    result.add_argument("--refresh-catalog", action="store_true", help="Refresh the official ATE cache")
    result.add_argument("--top", type=int, default=10, help="Candidates per project (default: 10)")
    result.add_argument("--max-files", type=int, default=1_000, help="Maximum filenames per project")
    result.add_argument(
        "--include-agent-configs",
        action="store_true",
        help="Read recognized agent configuration keys outside the selected projects",
    )
    result.add_argument("--offline", action="store_true", help="Skip repository lookups; requires a cached or local catalog")
    result.add_argument("--output", type=Path, help="Write Markdown to this file")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.top < 1 or arguments.top > 100:
        parser().error("--top must be between 1 and 100")
    catalog = arguments.catalog or default_cache_path()
    if not catalog.is_file():
        if arguments.offline:
            parser().error(f"offline catalog not found: {catalog}")
        print("Downloading Cohere Labs ATE matches from the official Hugging Face API...", file=sys.stderr)
        try:
            download_catalog(catalog, refresh=arguments.refresh_catalog)
        except RuntimeError as error:
            parser().error(str(error))
    elif arguments.refresh_catalog and not arguments.catalog:
        download_catalog(catalog, refresh=True)

    reports: list[str] = []
    for supplied in arguments.paths:
        try:
            context = collect_context(
                supplied,
                max_files=max(1, arguments.max_files),
                include_agent_configs=arguments.include_agent_configs,
            )
        except ValueError as error:
            print(f"Skipping {supplied}: {error}", file=sys.stderr)
            continue
        candidates = rank_candidates(context, iter_catalog(catalog), limit=arguments.top)
        enrich_candidates(candidates, offline=arguments.offline)
        reports.append(render_report(context, candidates))
    if not reports:
        return 2
    rendered = "\n\n---\n\n".join(reports)
    if arguments.output:
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {arguments.output}", file=sys.stderr)
    else:
        print(rendered)
    return 0
