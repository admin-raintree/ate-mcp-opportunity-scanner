# Security

## Report a vulnerability

Do not open a public issue for a suspected vulnerability. Send a private report through GitHub's private vulnerability reporting feature when it is available for this repository.

Include the affected version, reproduction steps, impact, and any suggested remediation. Do not include credentials or private project content.

## Trust model

The scanner treats project paths, filenames, manifests, ATE rows, repository metadata, and tool descriptions as untrusted data.

The scanner must:

- Read only the user-selected project folders.
- Read recognized agent configurations outside those folders only after the user passes `--include-agent-configs`.
- Reject filesystem-root scans.
- Skip symlinks, credential files, environment files, private keys, generated folders, and oversized files.
- Extract keys only from MCP and agent JSON configurations.
- Extract MCP server table names only from recognized JSON and TOML configurations; do not retain their commands, arguments, URLs, environment values, or headers.
- Avoid executing project files, manifest scripts, MCP servers, or downloaded code.
- Avoid sending project content, project terms, paths, or scanner reports to network services.
- Send only public ATE identifiers and public repository identifiers when resolving candidate metadata.
- Keep scanner reports local unless the user publishes them.

## Candidate screening

Risk labels identify words associated with destructive or state-changing actions. Repository screens check limited public metadata such as archive status, detected license, and last update. Neither mechanism is a security audit.

Review a candidate's source code, dependency chain, requested permissions, authentication, data destinations, destructive operations, and maintenance before installation.
