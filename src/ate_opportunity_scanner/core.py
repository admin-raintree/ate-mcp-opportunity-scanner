"""Local metadata collection, ranking, and candidate screening."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Mapping


DATASET = "CohereLabs/ATE"
DATASET_API = "https://datasets-server.huggingface.co"
USER_AGENT = "ate-mcp-opportunity-scanner/0.1 (+https://github.com/admin-raintree/ate-mcp-opportunity-scanner)"
MAX_FILE_BYTES = 256_000
MAX_FILES = 1_000
MAX_DOWNLOAD_BYTES = 256_000_000
MAX_CATALOG_ROWS = 100_000
TOKEN_RE = re.compile(r"[a-z][a-z0-9+#.-]{2,}")
URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")

IGNORED_PARTS = {
    ".git", ".github", ".hg", ".svn", ".next", ".venv", "venv", "__pycache__",
    "build", "dist", "node_modules", "target", "vendor", ".cache",
}
SENSITIVE_NAMES = {
    ".env", ".env.local", ".npmrc", ".pypirc", "credentials.json", "secrets.json",
    "id_rsa", "id_ed25519", "known_hosts", "authorized_keys",
}
MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "cargo.toml", "go.mod",
    "gemfile", "composer.json", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "mcp.json", ".mcp.json", ".claude.json", "config.toml", "agents.md", "claude.md", "cursor.md", ".cursorrules",
    "readme.md", "readme.txt",
}
STOP_WORDS = {
    "about", "after", "again", "against", "all", "also", "and", "any", "are", "because",
    "before", "being", "both", "build", "can", "could", "does", "each", "final", "first",
    "for", "from", "have", "how", "into", "its", "may", "more", "most", "must", "new",
    "next", "not", "only", "other", "our", "over", "project", "required", "should", "some",
    "than", "that", "the", "their", "then", "there", "these", "they", "this", "through",
    "tool", "tools", "under", "use", "using", "was", "were", "when", "where", "which",
    "will", "with", "would", "you", "your",
}
CAPABILITY_EXPANSIONS = {
    "react": {"frontend", "browser", "typescript", "accessibility"},
    "nextjs": {"frontend", "browser", "typescript", "deployment"},
    "typescript": {"javascript", "frontend", "node"},
    "postgres": {"database", "sql", "query"},
    "mysql": {"database", "sql", "query"},
    "sqlite": {"database", "sql", "query"},
    "pytest": {"testing", "python", "quality"},
    "playwright": {"browser", "testing", "accessibility"},
    "github": {"repository", "issues", "pull", "deployment"},
    "docker": {"container", "deployment", "infrastructure"},
    "terraform": {"infrastructure", "cloud", "deployment"},
    "pdf": {"document", "extract", "convert"},
    "spreadsheet": {"excel", "data", "table"},
    "analytics": {"data", "chart", "visualization"},
}
FILE_CAPABILITIES = {
    ".py": {"python", "testing", "code"},
    ".js": {"javascript", "node", "code"},
    ".jsx": {"javascript", "react", "frontend"},
    ".ts": {"typescript", "node", "code"},
    ".tsx": {"typescript", "react", "frontend"},
    ".swift": {"swift", "apple", "ios"},
    ".go": {"golang", "backend", "code"},
    ".rs": {"rust", "backend", "code"},
    ".md": {"markdown", "documentation"},
    ".pdf": {"pdf", "document"},
    ".sql": {"sql", "database"},
}
OPPORTUNITY_PROFILES = {
    "Web quality": (
        {"react", "nextjs", "frontend", "typescript", "javascript", "website", "html", "css"},
        {"accessibility", "browser", "playwright", "screenshot", "visual", "testing", "performance", "lighthouse"},
    ),
    "Documentation and knowledge": (
        {"documentation", "markdown", "docs", "knowledge", "standards", "readme"},
        {"documentation", "markdown", "search", "index", "links", "convert", "summarize", "knowledge"},
    ),
    "Database operations": (
        {"database", "sql", "postgres", "mysql", "sqlite", "prisma", "schema"},
        {"database", "query", "schema", "migration", "postgres", "sql", "backup", "performance"},
    ),
    "Security review": (
        {"security", "scanner", "authentication", "authorization", "vulnerability", "audit"},
        {"security", "vulnerability", "audit", "scan", "dependency", "permissions", "secrets"},
    ),
    "Media processing": (
        {"music", "audio", "video", "image", "media", "podcast"},
        {"audio", "transcribe", "metadata", "video", "image", "convert", "caption"},
    ),
    "Financial analysis": (
        {"finance", "financial", "portfolio", "trading", "market", "accounting"},
        {"finance", "market", "price", "portfolio", "chart", "analysis", "transaction"},
    ),
    "Agent engineering": (
        {"agent", "agents", "mcp", "codex", "claude", "cursor", "prompt"},
        {"agent", "mcp", "evaluation", "trace", "prompt", "memory", "observability", "testing"},
    ),
    "Code maintenance": (
        {"python", "javascript", "typescript", "golang", "rust", "swift", "code", "backend"},
        {"testing", "review", "debug", "refactor", "coverage", "dependency", "analysis", "quality"},
    ),
}
AGGREGATOR_MARKERS = {"awesome", "skillranking", "ecosystem", "collection", "directory"}
HIGH_RISK_TERMS = {
    "delete", "irreversible", "payment", "purchase", "refund", "shell", "terminal",
    "credential", "secret", "private-key", "sudo", "deploy", "execute", "trade",
}
MEDIUM_RISK_TERMS = {
    "create", "edit", "update", "write", "send", "upload", "download", "browser",
    "network", "email", "message", "database", "filesystem",
}
SAFE_REPORT_SIGNALS = (
    set(CAPABILITY_EXPANSIONS)
    | set().union(*CAPABILITY_EXPANSIONS.values())
    | set().union(*(triggers | goals for triggers, goals in OPPORTUNITY_PROFILES.values()))
    | set().union(*FILE_CAPABILITIES.values())
)


@dataclass
class ProjectContext:
    root: Path
    terms: Counter[str] = field(default_factory=Counter)
    metadata_files: list[str] = field(default_factory=list)
    detected_agents: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    installed_servers: set[str] = field(default_factory=set)
    files_seen: int = 0
    files_skipped: int = 0


@dataclass
class Candidate:
    score: float
    row: dict[str, str]
    signals: list[str]
    risk_level: str
    risk_signals: list[str]
    repository: dict[str, object] | None = None


def tokenize(text: str) -> Counter[str]:
    normalized = text.lower().replace("next.js", "nextjs").replace("model context protocol", "mcp")
    return Counter(
        token for token in TOKEN_RE.findall(normalized)
        if token not in STOP_WORDS and not looks_sensitive(token)
    )


def looks_sensitive(token: str) -> bool:
    if len(token) > 30:
        return True
    digits = sum(character.isdigit() for character in token)
    return digits > max(4, len(token) // 3)


def expand_capabilities(terms: Counter[str]) -> None:
    additions: Counter[str] = Counter()
    for term, count in terms.items():
        for related in CAPABILITY_EXPANSIONS.get(term, set()):
            additions[related] += max(1, count // 2)
    terms.update(additions)


def _approved_json_metadata(path: Path, value: object) -> list[str]:
    """Return non-secret JSON metadata. MCP and agent configs contribute keys only."""
    strings: list[str] = []
    lower_name = path.name.lower()

    def keys_only(item: object, depth: int = 0) -> None:
        if depth > 6:
            return
        if isinstance(item, dict):
            for key, child in item.items():
                strings.append(str(key))
                keys_only(child, depth + 1)
        elif isinstance(item, list):
            for child in item[:100]:
                if isinstance(child, (dict, list)):
                    keys_only(child, depth + 1)

    if lower_name in {"mcp.json", ".mcp.json"} or any(
        part in {".codex", ".claude", ".cursor", ".grok"} for part in path.parts
    ):
        keys_only(value)
        return strings

    if lower_name == "package.json" and isinstance(value, dict):
        for key in ("name", "description"):
            item = value.get(key)
            if isinstance(item, str) and len(item) <= 500:
                strings.append(item)
        keywords = value.get("keywords", [])
        if isinstance(keywords, list):
            strings.extend(str(item) for item in keywords[:100])
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            item = value.get(key, {})
            if isinstance(item, dict):
                strings.extend(str(name) for name in item)
        scripts = value.get("scripts", {})
        if isinstance(scripts, dict):
            strings.extend(str(name) for name in scripts)
        return strings

    keys_only(value)
    return strings


def metadata_terms(path: Path) -> Counter[str]:
    try:
        if path.is_symlink() or path.name.lower() in SENSITIVE_NAMES:
            return Counter()
        if path.stat().st_size > MAX_FILE_BYTES:
            return Counter()
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return Counter()

    lower_name = path.name.lower()
    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return Counter()
        return tokenize(" ".join(_approved_json_metadata(path, parsed)))
    if lower_name in {"agents.md", "claude.md", "cursor.md", ".cursorrules", "readme.md", "readme.txt"}:
        headings = [line.lstrip("# ") for line in raw.splitlines() if line.startswith("#")]
        return tokenize(" ".join(headings))
    if lower_name in {"requirements.txt", "go.mod", "gemfile"}:
        safe_lines = [line.split("#", 1)[0] for line in raw.splitlines() if not any(word in line.lower() for word in ("token", "password", "secret"))]
        return tokenize(" ".join(safe_lines))
    if lower_name in {"pyproject.toml", "cargo.toml", "config.toml"}:
        try:
            import tomllib
            parsed = tomllib.loads(raw)
        except (ValueError, TypeError):
            return Counter()
        return tokenize(" ".join(_approved_json_metadata(path, parsed)))
    return tokenize(" ".join(re.findall(r"^[A-Za-z][A-Za-z0-9_.-]*:", raw, re.MULTILINE)))


def detect_agents() -> list[str]:
    home = Path.home()
    candidates = {
        "Codex": home / ".codex",
        "Claude Code": home / ".claude",
        "Cursor": home / ".cursor",
        "Grok-compatible config": home / ".grok",
    }
    return [name for name, path in candidates.items() if path.is_dir()]


def configured_server_names(path: Path) -> set[str]:
    """Read MCP server keys without retaining commands, arguments, URLs, or credentials."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return set()
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() == ".json":
            value = json.loads(raw)
        else:
            import tomllib
            value = tomllib.loads(raw)
    except (OSError, ValueError, TypeError):
        return set()
    if not isinstance(value, dict):
        return set()
    servers = value.get("mcpServers") or value.get("mcp_servers")
    if not isinstance(servers, dict):
        return set()
    return {str(name).lower() for name in servers}


def detected_server_names() -> set[str]:
    home = Path.home()
    paths = [
        home / ".codex" / "config.toml",
        home / ".claude.json",
        home / ".claude" / "settings.json",
        home / ".cursor" / "mcp.json",
        home / ".grok" / "config.toml",
    ]
    result: set[str] = set()
    for path in paths:
        result.update(configured_server_names(path))
    return result


def collect_context(
    root: Path,
    max_files: int = MAX_FILES,
    include_agent_configs: bool = False,
) -> ProjectContext:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    if root == Path(root.anchor):
        raise ValueError("refusing to scan a filesystem root; select project folders")

    context = ProjectContext(
        root=root,
        detected_agents=detect_agents() if include_agent_configs else [],
        installed_servers=detected_server_names() if include_agent_configs else set(),
    )
    context.terms.update(tokenize(root.name))
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names[:] = sorted(
            name for name in directory_names
            if name not in IGNORED_PARTS and not (Path(current) / name).is_symlink()
        )
        relative_current = Path(current).relative_to(root)
        if relative_current.parts:
            context.terms.update(tokenize(" ".join(relative_current.parts)))
        for filename in sorted(file_names):
            if context.files_seen >= max_files:
                context.files_skipped += 1
                continue
            context.files_seen += 1
            path = Path(current) / filename
            if filename.lower() in SENSITIVE_NAMES or path.is_symlink():
                context.files_skipped += 1
                continue
            context.terms.update(tokenize(filename))
            for capability in FILE_CAPABILITIES.get(path.suffix.lower(), set()):
                context.terms[capability] += 1
            if filename.lower() in MANIFEST_NAMES:
                context.installed_servers.update(configured_server_names(path))
                terms = metadata_terms(path)
                if terms:
                    context.terms.update(terms)
                    context.metadata_files.append(str(path.relative_to(root)))
    expand_capabilities(context.terms)
    context.opportunities = [
        name for name, (triggers, _) in OPPORTUNITY_PROFILES.items()
        if set(context.terms).intersection(triggers)
    ]
    return context


def default_cache_path() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "ate-mcp-opportunity-scanner" / "onet-good.jsonl"


def _request_json(endpoint: str, parameters: Mapping[str, str | int], retries: int = 7) -> dict:
    url = f"{DATASET_API}/{endpoint}?{urllib.parse.urlencode(parameters)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    delay = 1.0
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read(10_000_001)
                if len(payload) > 10_000_000:
                    raise RuntimeError("dataset response exceeded the size limit")
                result = json.loads(payload)
            if "error" not in result:
                return result
            last_error = RuntimeError(str(result["error"]))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
        time.sleep(delay)
        delay = min(delay * 2, 20)
    raise RuntimeError(f"dataset request failed: {last_error}")


def _download_file(url: str, destination: Path, expected_size: int) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "huggingface.co":
        raise RuntimeError("refusing a dataset download outside https://huggingface.co")
    if expected_size < 1 or expected_size > MAX_DOWNLOAD_BYTES:
        raise RuntimeError(f"refusing unexpected dataset size: {expected_size} bytes")

    def allowed_redirect(target: str) -> bool:
        target_url = urllib.parse.urlparse(target)
        hostname = target_url.hostname or ""
        return target_url.scheme == "https" and (
            hostname == "huggingface.co"
            or hostname.endswith(".huggingface.co")
            or hostname.endswith(".hf.co")
        )

    class RestrictedRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, newurl):
            if not allowed_redirect(newurl):
                raise urllib.error.HTTPError(newurl, code, "refused download redirect", headers, fp)
            return super().redirect_request(request, fp, code, message, headers, newurl)

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(RestrictedRedirectHandler())
    with opener.open(request, timeout=120) as response, destination.open("wb") as handle:
        if not allowed_redirect(response.geturl()):
            raise RuntimeError("refusing an unexpected final dataset URL")
        remaining = expected_size + 1
        while remaining:
            chunk = response.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            handle.write(chunk)
            remaining -= len(chunk)
    actual_size = destination.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError(f"dataset download size mismatch: received {actual_size}, expected {expected_size}")


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def _parquet_sources() -> dict[str, tuple[str, int]]:
    result = _request_json("parquet", {"dataset": DATASET}, retries=4)
    sources: dict[str, tuple[str, int]] = {}
    for item in result.get("parquet_files", []):
        if item.get("split") == "train" and item.get("config") in {"onet_matches", "servers"}:
            sources[str(item["config"])] = (str(item["url"]), int(item["size"]))
    if set(sources) != {"onet_matches", "servers"}:
        raise RuntimeError("official ATE Parquet files were not available")
    return sources


def _download_catalog_with_duckdb(destination: Path, duckdb: str) -> Path:
    sources = _parquet_sources()
    destination.parent.mkdir(parents=True, exist_ok=True)
    matches_path = destination.with_name("onet_matches.download.parquet")
    servers_path = destination.with_name("servers.download.parquet")
    temporary = destination.with_suffix(".tmp")
    try:
        matches_url, matches_size = sources["onet_matches"]
        servers_url, servers_size = sources["servers"]
        _download_file(matches_url, matches_path, matches_size)
        _download_file(servers_url, servers_path, servers_size)
        sql = f"""
        COPY (
            SELECT
                matches.mcp_id,
                matches.tool_id,
                matches.server_name,
                matches.tool_name,
                matches.tool_description,
                matches.task_id,
                matches.task_text,
                matches.occupation_title,
                matches.soc_code,
                matches.cosine_similarity,
                matches.match_quality,
                matches.match_notes,
                servers.github_url,
                servers.github_stargazers_count,
                servers.github_archived,
                servers.github_pushed_at
            FROM read_parquet('{_sql_path(matches_path)}') AS matches
            LEFT JOIN read_parquet('{_sql_path(servers_path)}') AS servers USING (mcp_id)
            WHERE matches.match_quality = 'good'
        ) TO '{_sql_path(temporary)}' (FORMAT JSON, ARRAY false);
        """
        completed = subprocess.run(
            [duckdb, "-c", sql], check=False, capture_output=True, text=True, timeout=120
        )
        if completed.returncode != 0:
            raise RuntimeError(f"DuckDB catalog extraction failed: {completed.stderr.strip()}")
        if temporary.stat().st_size > MAX_DOWNLOAD_BYTES:
            raise RuntimeError("extracted catalog exceeded the local size limit")
        temporary.replace(destination)
        return destination
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(f"fast catalog build failed: {error}") from error
    finally:
        matches_path.unlink(missing_ok=True)
        servers_path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


def _download_catalog_via_api(destination: Path) -> Path:
    parameters: dict[str, str | int] = {
        "dataset": DATASET,
        "config": "onet_matches",
        "split": "train",
        "where": '"match_quality"=\'good\'',
        "offset": 0,
        "length": 100,
    }
    first = _request_json("filter", parameters)
    total = int(first.get("num_rows_total", len(first.get("rows", []))))
    if total < 1 or total > MAX_CATALOG_ROWS:
        raise RuntimeError(f"refusing unexpected catalog row count: {total}")
    first_rows = first.get("rows", [])
    page_size = int(first.get("num_rows_per_page") or len(first_rows) or 100)
    pages: dict[int, list[dict]] = {0: first_rows}

    def fetch_page(offset: int) -> tuple[int, list[dict]]:
        page_parameters = dict(parameters)
        page_parameters["offset"] = offset
        page = _request_json("filter", page_parameters)
        return offset, page.get("rows", [])

    offsets = list(range(page_size, total, page_size))
    if offsets:
        with ThreadPoolExecutor(max_workers=min(8, len(offsets))) as executor:
            futures = [executor.submit(fetch_page, offset) for offset in offsets]
            for future in as_completed(futures):
                offset, rows = future.result()
                pages[offset] = rows

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    written = 0
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            for offset in sorted(pages):
                rows = pages[offset]
                written += len(rows)
                for wrapped in rows:
                    row = wrapped.get("row", wrapped)
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        if written != total:
            raise RuntimeError(f"catalog download returned {written} rows; expected {total}")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def download_catalog(destination: Path, refresh: bool = False) -> Path:
    if destination.is_file() and not refresh:
        return destination
    duckdb = shutil.which("duckdb")
    if duckdb:
        resolved_duckdb = Path(duckdb).resolve()
        working_directory = Path.cwd().resolve()
        if resolved_duckdb == working_directory or working_directory in resolved_duckdb.parents:
            duckdb = None
        else:
            duckdb = str(resolved_duckdb)
    if duckdb:
        return _download_catalog_with_duckdb(destination, duckdb)
    return _download_catalog_via_api(destination)


def iter_catalog(path: Path) -> Iterator[dict[str, str]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            yield from csv.DictReader(handle)
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def classify_risk(text: str) -> tuple[str, list[str]]:
    terms = set(tokenize(text))
    high = sorted(terms.intersection(HIGH_RISK_TERMS))
    medium = sorted(terms.intersection(MEDIUM_RISK_TERMS))
    if high:
        return "high", high
    if medium:
        return "medium", medium
    return "low", []


def rank_candidates(context: ProjectContext, rows: Iterable[dict[str, str]], limit: int = 20) -> list[Candidate]:
    prepared: list[tuple[dict[str, str], Counter[str]]] = []
    document_frequency: Counter[str] = Counter()
    for row in rows:
        description = str(row.get("tool_description") or "").strip()
        server_name = str(row.get("server_name") or "").lower()
        if server_name in context.installed_servers:
            continue
        if len(description) < 20 or any(marker in server_name for marker in AGGREGATOR_MARKERS):
            continue
        candidate_terms = tokenize(" ".join(str(row.get(key, "")) for key in (
            "tool_name", "server_name", "tool_description", "task_text", "occupation_title"
        )))
        expand_capabilities(candidate_terms)
        prepared.append((row, candidate_terms))
        document_frequency.update(candidate_terms.keys())

    document_count = max(len(prepared), 1)
    ranked: list[Candidate] = []
    context_terms = set(context.terms)
    for row, candidate_terms in prepared:
        opportunity_hits: dict[str, set[str]] = {}
        for name in context.opportunities:
            goals = OPPORTUNITY_PROFILES[name][1]
            hits = set(candidate_terms).intersection(goals)
            if hits:
                opportunity_hits[name] = hits
        weighted: dict[str, float] = {}
        for term in context_terms.intersection(candidate_terms):
            frequency = document_frequency[term]
            if document_count >= 20 and frequency / document_count >= 0.15:
                continue
            inverse_frequency = math.log((document_count + 1) / (frequency + 1)) + 1
            weighted[term] = inverse_frequency * (1 + math.log1p(context.terms[term]))
        profile_term_count = len(set().union(*opportunity_hits.values())) if opportunity_hits else 0
        if len(weighted) < 2 and profile_term_count < 2:
            continue
        numerator = sum(
            weight
            * (math.log((document_count + 1) / (document_frequency[term] + 1)) + 1)
            * (1 + math.log1p(candidate_terms[term]))
            for term, weight in weighted.items()
        )
        norm = math.sqrt(sum(
            ((math.log((document_count + 1) / (document_frequency[term] + 1)) + 1) * (1 + math.log1p(count))) ** 2
            for term, count in candidate_terms.items()
        ))
        score = numerator / max(norm, 1.0)
        score += sum(8.0 + 4.0 * len(hits) for hits in opportunity_hits.values())
        stars = row.get("github_stargazers_count")
        try:
            score += min(math.sqrt(max(float(stars), 0.0)), 50.0) / 2.0
        except (TypeError, ValueError):
            pass
        description = f"{row.get('tool_name', '')} {row.get('tool_description', '')}"
        risk_level, risk_signals = classify_risk(description)
        if risk_level == "high":
            score *= 0.75
        elif risk_level == "medium":
            score *= 0.9
        ranked.append(Candidate(
            score=score,
            row=row,
            signals=(
                [f"{name}: {', '.join(sorted(hits))}" for name, hits in opportunity_hits.items()]
                + [
                    term for term in sorted(weighted, key=weighted.get, reverse=True)
                    if term in SAFE_REPORT_SIGNALS
                ]
            )[:8],
            risk_level=risk_level,
            risk_signals=risk_signals,
        ))

    ranked.sort(key=lambda candidate: candidate.score, reverse=True)
    results: list[Candidate] = []
    seen: set[str] = set()
    for candidate in ranked:
        identity = re.sub(r"[^a-z0-9]+", "", str(candidate.row.get("tool_name") or "").lower())
        if not identity:
            identity = str(candidate.row.get("mcp_id") or candidate.row.get("server_name"))
        if identity in seen:
            continue
        seen.add(identity)
        results.append(candidate)
        if len(results) >= limit:
            break
    return results


def resolve_server(mcp_id: str) -> dict[str, object] | None:
    if not re.fullmatch(r"[0-9a-f]{16}", mcp_id):
        return None
    result = _request_json("filter", {
        "dataset": DATASET,
        "config": "servers",
        "split": "train",
        "where": f'"mcp_id"=\'{mcp_id}\'',
        "offset": 0,
        "length": 1,
    }, retries=3)
    rows = result.get("rows", [])
    if not rows:
        return None
    return rows[0].get("row", rows[0])


def github_health(repository_url: str) -> dict[str, object]:
    match = URL_RE.match(repository_url)
    if not match:
        return {"status": "unknown", "warning": "Repository URL is not a recognized GitHub URL."}
    owner, repository = match.groups()
    url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repository)}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return {"status": "unknown", "warning": f"GitHub health lookup failed: {type(error).__name__}"}
    warnings: list[str] = []
    if data.get("archived"):
        warnings.append("Repository is archived.")
    if data.get("license") is None:
        warnings.append("No repository license was detected.")
    pushed = data.get("pushed_at")
    if isinstance(pushed, str):
        try:
            pushed_at = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - pushed_at).days > 730:
                warnings.append("Repository has not been updated for more than two years.")
        except ValueError:
            pass
    return {
        "status": "warning" if warnings else "screened",
        "stars": data.get("stargazers_count"),
        "license": (data.get("license") or {}).get("spdx_id") if isinstance(data.get("license"), dict) else None,
        "pushed_at": pushed,
        "warnings": warnings,
    }


def enrich_candidates(candidates: list[Candidate], offline: bool = False) -> None:
    for candidate in candidates:
        repository_url = candidate.row.get("github_url")
        repository_match = URL_RE.match(str(repository_url or ""))
        if repository_match:
            owner, repository_name = repository_match.groups()
            repository_url = f"https://github.com/{owner}/{repository_name}"
            warnings: list[str] = []
            if str(candidate.row.get("github_archived", "")).lower() == "true":
                warnings.append("ATE recorded this repository as archived.")
            candidate.repository = {
                "url": repository_url,
                "status": "ATE metadata only" if offline else "pending live screen",
                "warnings": warnings,
            }
        else:
            repository_url = None
        if offline:
            continue
        server: dict[str, object] | None = None
        if not repository_url:
            try:
                server = resolve_server(str(candidate.row.get("mcp_id", "")))
            except RuntimeError:
                server = None
            if server:
                repository_url = str(server.get("github_url") or "")
        resolved_match = URL_RE.match(str(repository_url or ""))
        if resolved_match:
            owner, repository_name = resolved_match.groups()
            repository_url = f"https://github.com/{owner}/{repository_name}"
            health = github_health(repository_url)
            candidate.repository = {"url": repository_url, **health}


def render_report(context: ProjectContext, candidates: list[Candidate]) -> str:
    def safe(value: object) -> str:
        text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value))
        text = text.replace("\\", "\\\\")
        for character in ("`", "*", "_", "[", "]", "<", ">"):
            text = text.replace(character, f"\\{character}")
        return text

    lines = [
        f"# MCP opportunities for {safe(context.root.name)}", "",
        f"Scanned locally at {datetime.now(timezone.utc).isoformat()}. No project content was uploaded.", "",
        f"Detected agent surfaces: {', '.join(context.detected_agents) if context.detected_agents else 'none'}", "",
        f"Opportunity classes: {', '.join(context.opportunities) if context.opportunities else 'no strong signal'}", "",
        f"Existing MCP server names compared without reading configuration values: {len(context.installed_servers)}", "",
        f"Reviewed {context.files_seen} filenames and {len(context.metadata_files)} approved metadata files.", "",
        "## Candidates", "",
    ]
    for index, candidate in enumerate(candidates, 1):
        row = candidate.row
        name = safe(row.get("tool_name") or "Unnamed tool")
        server = safe(row.get("server_name") or "Unknown server")
        description = safe(re.sub(r"\s+", " ", str(row.get("tool_description") or row.get("task_text") or "No description"))[:500])
        lines.extend([
            f"{index}. **{name}** from **{server}**", "",
            f"   - Possible use: {description}",
            f"   - Matching signals: {safe(', '.join(candidate.signals))}",
            f"   - Action risk: {candidate.risk_level}" + (f" ({', '.join(candidate.risk_signals)})" if candidate.risk_signals else ""),
        ])
        if candidate.repository:
            lines.append(f"   - Repository: {safe(candidate.repository.get('url'))}")
            lines.append(f"   - Repository screen: {safe(candidate.repository.get('status'))}")
            warnings = candidate.repository.get("warnings")
            if warnings:
                lines.append(f"   - Repository warnings: {safe(' '.join(str(item) for item in warnings))}")
        else:
            lines.append("   - Repository: unresolved; search and verify the server manually")
        lines.extend([f"   - Match score: {candidate.score:.1f}", ""])
    lines.extend([
        "## Interpretation", "",
        "These results are discovery leads, not compatibility or security approvals. Cohere classified tool descriptions with a language model; it did not execute the tools. Review source code, permissions, maintenance, data handling, and destructive actions before installation.", "",
    ])
    return "\n".join(lines)
