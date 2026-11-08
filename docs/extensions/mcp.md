# MCP and External Tools (A5) — Reference Only

This repository does not configure an MCP server. This page describes the governed pattern for a team that decides to use one. The demonstrator excludes MCP because no scenario needs it, and a live server adds a third-party process, credentials and a data path.

## Why MCP needs separate controls

- An MCP server is a separate process with its own permissions. Agent sandboxes do not always contain it. Claude Code runs local MCP servers outside its Bash sandbox. The GitHub Copilot cloud agent firewall does not apply directly to MCP server processes.
- A server can receive any context that the agent sends to it.
- Tool output is untrusted content. It can contain instructions that try to change the agent's task (A6).
- The MCP security best practices (revision 2025-11-25) describe confused-deputy attacks. They prohibit token passthrough. A server must not forward a client token to another API. It must first check that the token was issued for that server.

## Governed pattern

1. **Deny by default.** No server is approved until the governance owner adds it to `governance/approved-tools.yaml`.
2. **Approve each server.** Record the purpose, the vendor, the version, the data class that the server may receive and the owner.
3. **Use the smallest tool set.** Enable only the tools that the task needs. Use read-only mode where the server offers it.
4. **Use narrow, short-lived credentials.** Use a token that is scoped to one repository, with an expiry date. Never use a personal token with broad scope.
5. **No token passthrough.** The server uses its own credentials for downstream APIs.
6. **Treat tool output as data.** Tool output cannot authorise a privileged action.
7. **Protect the configuration.** Put MCP configuration files under code-owner review (A7). For Claude Code, `.mcp.json` is a protected path for sandboxed commands.
8. **Test before you claim.** Before you claim any MCP control as enforced, test it safely. A local mock server that returns a fixed string is safer than a live integration.

## Where to configure

| Platform | Configuration | Notes |
|---|---|---|
| Claude Code | `.mcp.json` and `enabledMcpjsonServers` in settings. `mcp__<server>__<tool>` permission rules. | Local MCP servers run outside the Bash sandbox |
| VS Code (Copilot) | `.vscode/mcp.json`. `chat.agent.sandbox.mcpServers` for the VS Code sandbox. | The sandbox is preview |
| Copilot cloud agent | Repository settings, MCP configuration | The firewall does not apply directly to MCP server processes |
