# ATE MCP Opportunity Scanner

Find public Model Context Protocol (MCP) tools that may fit your local projects and agent setup. An MCP tool is a callable function. An MCP server provides one or more MCP tools.

The scanner reads a limited set of project metadata on your computer, compares it with Cohere Labs' Agentic Task Ecosystem (ATE), and writes a ranked candidate report. It does not install or execute MCP servers. It does not upload project content.

**Status:** Experimental alpha. Recommendations are discovery leads, not compatibility or security approvals.

## Why use it

On September 4, 2026, the official [ATE dataset endpoint](https://huggingface.co/datasets/CohereLabs/ATE) returned 18,058 tool-to-task matches classified as `good`. A catalog still does not tell you which MCP tools fit your work. This scanner starts with your project and identifies published MCP tools that may be relevant enough to investigate.

Use it to:

- Find possible automation, testing, documentation, data, and deployment integrations.
- Compare opportunities across several repositories.
- Rank candidates against concrete repository workflows such as tests, documentation, continuous integration, packaging, migrations, and deployment.
- Optionally detect Codex, Claude Code, Cursor, or Grok-compatible configuration folders.
- Optionally avoid recommending exact server names already present in recognized MCP configurations.
- Report transport-based compatibility evidence from ATE and public candidate repository metadata for Codex, Claude Code, Cursor, and Grok Build without claiming that an untested server works.
- Screen recommendations for permission signals, destructive actions, missing licenses, archived repositories, and stale maintenance.
- Generate an inert configuration review bundle that keeps every candidate disabled or outside a live client configuration.

## Privacy model

The scanner accepts only the folders that you name. It does not scan a filesystem root. When you pass `--include-agent-configs`, it also checks for recognized agent configuration folders and reads configured MCP server names. It does not read commands, arguments, URLs, headers, or environment values from those external configurations.

It reads:

- File and directory names, excluding common build, dependency, cache, and version-control folders.
- Dependency names and approved metadata from common project manifests.
- Markdown headings from `README.md`, `AGENTS.md`, `CLAUDE.md`, and Cursor rule files.
- Keys—but not values—from MCP and agent JSON configuration files.
- MCP server table names—but not commands, arguments, URLs, environment values, or headers—from recognized JSON and TOML configurations.

It skips `.env` files, credential files, private keys, symlinks, large files, source-file contents, conversation histories, and common generated folders. It sends public dataset queries to Hugging Face and public candidate repository identifiers to GitHub. For resolved candidates, it reads bounded public copies of `README.md`, `package.json`, `pyproject.toml`, `server.json`, and `.mcp.json` from the repository's reported default branch, falling back to `main`, to find explicit MCP transport declarations or local MCP command configurations. It does not send project names, paths, metadata, matching signals, or reports to either service. See the [security and privacy model](SECURITY.md) for the full boundary.

The scanner prints its report to the terminal by default. When you pass `--output`, it writes the report to that file instead. The report can contain the selected project's folder name, detected capability classes, the number of configured MCP server names, and recommendations. Terminal output can remain in shell history or captured logs. An output file remains at the selected location until you delete it.

The scanner caches only public ATE data at `${XDG_CACHE_HOME:-$HOME/.cache}/ate-mcp-opportunity-scanner/onet-good.jsonl`. It does not place project metadata in that cache. Delete the cache with:

```shell
rm "${XDG_CACHE_HOME:-$HOME/.cache}/ate-mcp-opportunity-scanner/onet-good.jsonl"
```

## Requirements

- Python 3.11 or later
- Internet access on the first run to read the official ATE dataset

The scanner has no third-party runtime dependencies.

The scanner requests catalog pages concurrently from the official Hugging Face filter API. Upstream availability and rate limits determine the completion time.

## Install

1. Clone the repository.

   ```shell
   git clone https://github.com/admin-raintree/ate-mcp-opportunity-scanner.git
   ```

2. Enter the repository and create a virtual environment.

   ```shell
   cd ate-mcp-opportunity-scanner
   python3 -m venv .venv
   ```

3. Install the scanner.

   ```shell
   .venv/bin/python -m pip install .
   ```

4. Confirm that the command is available.

   ```shell
   .venv/bin/ate-scan --help
   ```

   The command succeeds when it prints usage information beginning with `usage: ate-scan`.

## Scan projects

Scan one project:

```shell
.venv/bin/ate-scan /path/to/project --output recommendations.md
```

Scan several projects:

```shell
.venv/bin/ate-scan ~/Code/project-one ~/Code/project-two --output recommendations.md
```

Inspect only local data after the official catalog has been cached:

```shell
.venv/bin/ate-scan ~/Code/project-one --offline --output recommendations.md
```

Check recognized Codex, Claude Code, Cursor, and Grok configuration folders and configured MCP server names without reading configuration values:

```shell
.venv/bin/ate-scan ~/Code/project-one --include-agent-configs --output recommendations.md
```

Create a report and a separate configuration review bundle:

```shell
.venv/bin/ate-scan ~/Code/project-one \
  --output recommendations.md \
  --review-config mcp-configuration-review.md
```

The review bundle lists the candidates and provides one reusable template for each of Codex, Claude Code, Cursor, and Grok Build. Every suggested filename ends in `.review`. Codex and Grok templates also set `enabled = false`. Commands and read-only arguments remain explicit placeholders. The scanner does not write into the scanned project or change a client configuration.

The first online run requests rows classified as `good` from Hugging Face's Dataset Viewer API and stores the resulting public-data cache described under [Privacy model](#privacy-model). A successful run writes the requested files and prints their locations. This repository does not redistribute Cohere's dataset or upstream tool descriptions.

## Read the report

Each candidate includes:

- The published MCP tool description
- The project signals that contributed to its rank
- The concrete repository workflows it may support
- A low, medium, or high action-risk label
- Permission signals inferred from published metadata
- Transport-based compatibility evidence for each supported client
- A repository link when it can be resolved
- A maintenance state and repository or license warnings when available
- A security-review priority

Review every candidate before installation. A low action-risk label is not a security audit.

After reviewing a candidate, follow the [agent-specific MCP setup guide](docs/agent-setup.md) for Codex, Claude Code, Cursor, or Grok Build.

## Known limits

- Cohere used a language model to classify descriptions against occupational tasks. Cohere did not execute the tools.
- Some ATE classifications are implausible or overly broad.
- The local ranker combines term weighting with a small capability map. It does not understand a repository as deeply as a code reviewer.
- Repository screening cannot detect malicious code or prove compatibility.
- ATE metadata often omits the MCP transport. The scanner then checks bounded public repository documentation and package metadata. It reports compatibility as unknown when those files also lack explicit evidence.
- Client approval prompts and disabled templates do not prove that a server is read-only. A reviewer must verify and test a server-specific read-only mode before activation.
- The agent configuration check reports configuration-folder presence. It does not prove that an agent supports a recommended MCP server.
- Hugging Face may rate-limit or temporarily delay the first catalog build.

## Data and licenses

The scanner code is available under the [MIT License](LICENSE).

ATE remains on its publisher's service. The ATE repository does not currently specify a repository-level dataset license. O*NET material remains subject to its stated CC BY 4.0 terms, and upstream tool descriptions retain their original repository licenses. Review the [ATE dataset card](https://huggingface.co/datasets/CohereLabs/ATE) before reusing its content.

## Development

```shell
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change.

User-facing failure codes and recovery actions are documented in the [error reference](docs/errors.md).

## Sources

- [Cohere Labs ATE dataset](https://huggingface.co/datasets/CohereLabs/ATE)
- [Automation's Early Footprint](https://cohere.com/blog/automations-early-footprint)
- [Hugging Face Dataset Viewer filter API](https://huggingface.co/docs/dataset-viewer/filter)
- [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Claude Code MCP configuration](https://code.claude.com/docs/en/mcp)
- [Cursor MCP configuration](https://cursor.com/docs/mcp)
- [Grok Build MCP configuration](https://docs.x.ai/build/features/mcp-servers)

## Evaluation

See the [evaluation record](EVALUATION.md) for the available evidence, known gaps, and release criteria.
