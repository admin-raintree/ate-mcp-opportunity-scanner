"""Command-line interface."""

from __future__ import annotations

import argparse
import json
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
        help="Detect recognized agent folders and read configured MCP server names outside the selected projects",
    )
    result.add_argument("--offline", action="store_true", help="Skip repository lookups; requires a cached or local catalog")
    result.add_argument("--output", type=Path, help="Write Markdown to this file")
    return result


def main(argv: list[str] | None = None) -> int:
    argument_parser = parser()
    arguments = argument_parser.parse_args(argv)
    if arguments.top < 1 or arguments.top > 100:
        argument_parser.error("[ATE100] --top must be between 1 and 100. Choose a whole number in that range")
    catalog = arguments.catalog or default_cache_path()
    if not catalog.is_file():
        if arguments.offline:
            argument_parser.error(
                f"[ATE101] The offline catalog was not found at {catalog}. "
                "Run without --offline to download it, or pass --catalog with an existing file"
            )
        print("Downloading Cohere Labs ATE matches from the official Hugging Face API...", file=sys.stderr)
        try:
            download_catalog(catalog, refresh=arguments.refresh_catalog)
        except (RuntimeError, OSError):
            argument_parser.error(
                "[ATE102] The official ATE catalog could not be prepared. No complete cache was replaced. "
                "Check the network connection and retry, or pass --catalog with an existing file"
            )
    elif arguments.refresh_catalog and not arguments.catalog:
        try:
            download_catalog(catalog, refresh=True)
        except (RuntimeError, OSError):
            argument_parser.error(
                "[ATE102] The official ATE catalog could not be refreshed. The previous complete cache remains available. "
                "Check the network connection and retry"
            )

    reports: list[str] = []
    for supplied in arguments.paths:
        try:
            context = collect_context(
                supplied,
                max_files=max(1, arguments.max_files),
                include_agent_configs=arguments.include_agent_configs,
            )
        except ValueError as error:
            print(
                f"[ATE103] Skipped {supplied}: {error}. Choose an existing project directory.",
                file=sys.stderr,
            )
            continue
        try:
            candidates = rank_candidates(context, iter_catalog(catalog), limit=arguments.top)
        except (OSError, ValueError, json.JSONDecodeError, AttributeError, TypeError) as error:
            argument_parser.error(
                f"[ATE104] The catalog at {catalog} could not be read: {type(error).__name__}. "
                "Pass --catalog with a valid ATE JSONL or CSV file"
            )
        enrich_candidates(candidates, offline=arguments.offline)
        reports.append(render_report(context, candidates))
    if not reports:
        print(
            "[ATE105] No project was scanned. Correct the listed project paths and run the command again.",
            file=sys.stderr,
        )
        return 2
    rendered = "\n\n---\n\n".join(reports)
    if arguments.output:
        try:
            arguments.output.write_text(rendered + "\n", encoding="utf-8")
        except OSError as error:
            print(
                f"[ATE106] The report could not be written to {arguments.output}: "
                f"{type(error).__name__}. The output may be incomplete. Choose a new writable output path and run the command again.",
                file=sys.stderr,
            )
            return 2
        print(f"Wrote {arguments.output}", file=sys.stderr)
    else:
        print(rendered)
    return 0
