# Connect a reviewed MCP server

Use this guide only after you review a candidate's source, permissions, data destinations, maintenance, and installation instructions. The scanner does not verify that a server works with your agent.

Keep credentials in environment variables or the agent's supported credential store. Do not commit secrets to a project configuration.

## Codex

Codex supports local STDIO servers and remote Streamable HTTP servers. The ChatGPT desktop app, Codex CLI, and Codex IDE extension share host configuration.

Add a local STDIO server:

```shell
codex mcp add <server-name> -- <server-command> <arguments>
codex mcp list
```

Codex stores user configuration in `~/.codex/config.toml`. Trusted projects can use `.codex/config.toml`. Use environment-variable references for credentials and keep write-capable tools in prompt-based approval mode until you establish trust.

Follow the [official Codex MCP documentation](https://developers.openai.com/codex/mcp) for remote servers, OAuth, tool allowlists, and approval controls.

## Claude Code

Add a local STDIO server:

```shell
claude mcp add <server-name> -- <server-command> <arguments>
claude mcp list
```

Claude Code supports local, project, and user scopes. Project-scoped servers use `.mcp.json` and require project approval. Keep machine-specific credentials outside the shared file.

Follow the [official Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp) for scopes, remote transports, OAuth, and configuration import.

## Cursor

Cursor supports one-click MCP installation and custom `mcp.json` configuration. Use its interface when a reviewed server provides an official installation link. Otherwise, create the configuration using the server publisher's documented command or remote URL.

Follow the [official Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol) for supported transports, configuration locations, and authentication.

## Grok Build

Add a local STDIO server:

```shell
grok mcp add <server-name> -- <server-command> <arguments>
grok inspect
grok mcp doctor
```

Grok Build stores user settings in `~/.grok/config.toml` and project MCP settings in `.grok/config.toml`. It can also load compatible Claude and Cursor MCP configurations. Use environment-variable expansion instead of literal credentials.

Follow the [official Grok Build MCP documentation](https://docs.x.ai/build/features/mcp-servers) for scopes, configuration precedence, remote servers, and troubleshooting.
