English | [中文](./agents_CN.md)

# Using Lightroom Agent from your AI tool

Lightroom Agent ships two interfaces to the same operations:

- **Skill** (`skills/lightroom-agent/SKILL.md`): a workflow guide plus the `lightroom-agent` command. Best for coding
  agents that can run terminal commands and look at images (Claude Code, Codex, Gemini CLI, Cursor, WorkBuddy, Trae).
- **MCP server** (`lightroom-agent mcp`, stdio): tools such as `cull_photos`, `apply_style`, `view_image`. For chat
  apps that cannot run commands (Claude Desktop, Cherry Studio), and a good choice for any tool with MCP support.

Set up once from the repository (macOS / Windows):

```bash
git clone https://github.com/Runnerback/lightroom-agent.git
cd lightroom-agent
python3 scripts/install.py
```

The installer builds a private Python environment in `~/.lightroom-agent/`, puts `lightroom-agent` on your PATH,
installs the [Lightroom plugin](./install-plugin.md), links the skill into every AI tool it finds, and prints the MCP
command. Below, `<repo>` is the folder you cloned into. GUI apps do not see your shell's PATH, so MCP settings use the
full path:

| | MCP command | args |
|---|---|---|
| macOS | `<repo>/bin/lightroom-agent` | `["mcp"]` |
| Windows | `<repo>\bin\lightroom-agent.cmd` | `["mcp"]` |

Then, in any tool, just ask, for example: *"Cull the photos in the Lightroom collection 'Tokyo trip', show me the best
30, then try the Fuji film style on three of them."*

Pick a model that supports **tool calling** and **image input**: the agent looks at contact sheets to choose photos and
check colour.

---

## Claude Code

Install as a plugin (skill + MCP server, updates with `/plugin update`):

```text
/plugin marketplace add Runnerback/lightroom-agent
/plugin install lightroom-agent@lightroom-agent
```

The plugin brings its own copy of the code. The Lightroom plugin still has to be installed once: ask Claude to
"install the Lightroom plugin" (it runs `lightroom-agent install-plugin`), then restart Lightroom.

Alternative without the plugin system: the installer links the skill to `~/.claude/skills/lightroom-agent`, and

```bash
claude mcp add lightroom -- <repo>/bin/lightroom-agent mcp
```

## Claude Desktop

Settings › Developer › **Edit Config** opens `claude_desktop_config.json`. Add:

```json
{
  "mcpServers": {
    "lightroom": { "command": "<repo>/bin/lightroom-agent", "args": ["mcp"] }
  }
}
```

Restart Claude Desktop; the tools appear under the 🔨 / connectors menu.

## Codex (CLI, IDE extension, and the Codex app) — for ChatGPT users

The ChatGPT desktop / web app cannot start local MCP servers, so it cannot reach Lightroom on your computer. Use
**Codex**, signed in with your ChatGPT account.

Skill: the installer links it to `~/.codex/skills/lightroom-agent`. MCP (recommended for Codex, because its sandbox may
block the local network connection the CLI needs): add to `~/.codex/config.toml`

```toml
[mcp_servers.lightroom]
command = "<repo>/bin/lightroom-agent"
args = ["mcp"]
tool_timeout_sec = 900
```

or run `codex mcp add lightroom -- <repo>/bin/lightroom-agent mcp`.

## Gemini CLI

Skill: `gemini skills link <repo>/skills/lightroom-agent` (the installer links `~/.gemini/skills/lightroom-agent`).
The repository's `GEMINI.md` also points Gemini to the skill when you run it inside the repo.
MCP: in `~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "lightroom": { "command": "<repo>/bin/lightroom-agent", "args": ["mcp"], "timeout": 900000 }
  }
}
```

## Cursor

Skill: `~/.cursor/skills/lightroom-agent` (linked by the installer). MCP: Settings › MCP › **Add new global MCP
server**, or `~/.cursor/mcp.json` with the same `mcpServers` block as Claude Desktop.

## WorkBuddy (CodeBuddy)

Skill: the installer links `~/.workbuddy/skills/lightroom-agent`; or type **导入技能** in a chat and select the
`skills/lightroom-agent` folder. MCP: Settings › MCP › Add, and paste the `mcpServers` JSON above.

## Doubao models: Trae or Cherry Studio

The Doubao app cannot use local tools. Use Doubao models through an app that can:

- **Trae** (ByteDance's IDE, Doubao built in): skill in `~/.trae/skills/lightroom-agent` (linked by the installer);
  MCP: Settings › MCP › Add › **Add manually**, paste the `mcpServers` JSON above.
- **Cherry Studio**: add a Volcano Engine Ark (火山方舟) model provider with a Doubao vision model, then Settings ›
  MCP Servers › Add: type **stdio**, command `<repo>/bin/lightroom-agent`, arguments `mcp`. Enable the server in the
  chat's MCP menu.

## Other MCP clients

Any client that supports stdio MCP servers works the same way: command `<repo>/bin/lightroom-agent`, argument `mcp`.
Paste the content of `skills/lightroom-agent/SKILL.md` into the project / system instructions if the client has no
skill support: it contains the workflow and the quality checks.

## Notes

- The first run of `lightroom-agent` creates its Python environment (1–3 minutes, about 400 MB on disk).
- Long jobs (culling, styles) run in the background on the MCP server: the agent starts them and polls `job_status`.
