# ATE MCP Opportunity Scanner

Find public Model Context Protocol (MCP) tools that may fit your local projects and agent setup.

The scanner reads a limited set of project metadata on your computer, compares it with Cohere Labs' Agentic Task Ecosystem (ATE), and writes a ranked candidate report. It does not install or execute MCP servers. It does not upload project content.

**Status:** Experimental alpha. Recommendations are discovery leads, not compatibility or security approvals.

## Why use it

Public MCP directories contain hundreds of thousands of functions. A long catalog does not tell you which functions fit your work. This scanner starts with your project and answers a narrower question: which published tools appear relevant enough to investigate?

Use it to:

- Find possible automation, testing, documentation, data, and deployment integrations.
- Compare opportunities across several repositories.
- Optionally detect Codex, Claude Code, Cursor, or Grok-compatible configuration folders.
- Optionally avoid recommending exact server names already present in recognized MCP configurations.
- Screen recommendations for destructive actions, missing licenses, archived repositories, and stale maintenance.

## Privacy model

The scanner accepts only the folders that you name. It does not scan a filesystem root. It reads recognized agent configuration keys outside those folders only when you pass `--include-agent-configs`.

It reads:

- File and directory names, excluding common build, dependency, cache, and version-control folders.
- Dependency names and approved metadata from common project manifests.
- Markdown headings from `README.md`, `AGENTS.md`, `CLAUDE.md`, and Cursor rule files.
- Keys—but not values—from MCP and agent JSON configuration files.
- MCP server table names—but not commands, arguments, URLs, environment values, or headers—from recognized JSON and TOML configurations.

It skips `.env` files, credential files, private keys, symlinks, large files, source-file contents, conversation histories, and common generated folders. Repository-health requests contain only public candidate repository identifiers. See [SECURITY.md](SECURITY.md) for the full trust model.

## Requirements

- Python 3.11 or later
- Internet access on the first run to read the official ATE dataset

The scanner has no required third-party Python packages.

The optional `duckdb` command makes the first catalog build much faster. When it is available, the scanner downloads about 150 MB of official Parquet data, extracts the 18,058 matching rows, deletes the Parquet files, and retains a local cache of about 15 MB. Two measured development-machine runs completed in 26 and 53 seconds. Network and computer performance will change this time.

Without `duckdb`, the scanner uses the official Hugging Face filter API. That fallback can be much slower when the upstream index is cold.

## Install

```shell
git clone https://github.com/admin-raintree/ate-mcp-opportunity-scanner.git
cd ate-mcp-opportunity-scanner
python3 -m venv .venv
.venv/bin/python -m pip install .
```

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

Compare recognized Codex, Claude Code, Cursor, and Grok configuration keys without reading their values:

```shell
.venv/bin/ate-scan ~/Code/project-one --include-agent-configs --output recommendations.md
```

The first online run requests the rows classified as `good` directly from Hugging Face's Dataset Viewer API and stores them under your user cache. This repository does not redistribute Cohere's dataset or upstream tool descriptions.

## Read the report

Each candidate includes:

- A possible use based on the published description
- The project signals that contributed to its rank
- A low, medium, or high action-risk label
- A repository link when it can be resolved
- Repository maintenance and license warnings when available

Review every candidate before installation. A low action-risk label is not a security audit.

After reviewing a candidate, follow the [agent-specific MCP setup guide](docs/agent-setup.md) for Codex, Claude Code, Cursor, or Grok Build.

## Known limits

- Cohere used a language model to classify descriptions against occupational tasks. Cohere did not execute the tools.
- Some ATE classifications are implausible or overly broad.
- The local ranker combines term weighting with a small capability map. It does not understand a repository as deeply as a code reviewer.
- Repository screening cannot detect malicious code or prove compatibility.
- Agent detection reports configuration-folder presence. It does not prove that an agent supports a recommended server.
- Hugging Face may rate-limit or temporarily delay the first catalog build.

## Data and licenses

The scanner code is available under the [MIT License](LICENSE).

ATE remains on its publisher's service. The ATE repository does not currently specify a repository-level dataset license. O*NET material remains subject to its stated CC BY 4.0 terms, and upstream tool descriptions retain their original repository licenses. Review the [ATE dataset card](https://huggingface.co/datasets/CohereLabs/ATE) before reusing its content.

## Development

```shell
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change.

## Sources

- [Cohere Labs ATE dataset](https://huggingface.co/datasets/CohereLabs/ATE)
- [Automation's Early Footprint](https://cohere.com/blog/automations-early-footprint)
- [Hugging Face Dataset Viewer filter API](https://huggingface.co/docs/dataset-viewer/filter)

## Evaluation

See [EVALUATION.md](EVALUATION.md) for the current development-sample results. The evaluation measures discovery relevance, not compatibility or safety.
