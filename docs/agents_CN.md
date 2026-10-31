[English](./agents.md) | 中文

# 在各个 AI 工具里使用 Lightroom Agent

Lightroom Agent 提供两种接入方式,背后是同一套操作:

- **技能(Skill)**(`skills/lightroom-agent/SKILL.md`):工作流程说明 + `lightroom-agent` 命令。适合能执行终端命令、
  能看图片的编程类 Agent(Claude Code、Codex、Gemini CLI、Cursor、WorkBuddy、Trae)。
- **MCP 服务**(`lightroom-agent mcp`,stdio):提供 `cull_photos`、`apply_style`、`view_image` 等工具。适合不能执行
  命令的聊天客户端(Claude Desktop、Cherry Studio),任何支持 MCP 的工具也都可以用。

先在仓库里装一次(macOS / Windows):

```bash
git clone https://github.com/Runnerback/lightroom-agent.git
cd lightroom-agent
python3 scripts/install.py
```

安装脚本会在 `~/.lightroom-agent/` 建独立的 Python 环境,把 `lightroom-agent` 命令加到 PATH,安装
[Lightroom 插件](./install-plugin_CN.md),把技能链接到电脑上找到的每个 AI 工具,并打印 MCP 配置。下文的 `<repo>`
是你克隆的目录。图形界面的应用读不到终端的 PATH,所以 MCP 配置里要写完整路径:

| | MCP 命令 | 参数 |
|---|---|---|
| macOS | `<repo>/bin/lightroom-agent` | `["mcp"]` |
| Windows | `<repo>\bin\lightroom-agent.cmd` | `["mcp"]` |

之后在任意工具里直接说,例如:*"帮我把 Lightroom 收藏集『东京旅行』选一遍片,挑出最好的 30 张给我看,再挑 3 张试一下富士胶片风格。"*

请选择支持**工具调用**和**图片输入**的模型:AI 需要看小样图来选片和检查颜色。

---

## Claude Code

作为插件安装(技能 + MCP 一起装,用 `/plugin update` 更新):

```text
/plugin marketplace add Runnerback/lightroom-agent
/plugin install lightroom-agent@lightroom-agent
```

插件自带一份代码。Lightroom 插件仍需安装一次:对 Claude 说"安装 Lightroom 插件"(它会运行
`lightroom-agent install-plugin`),然后重启 Lightroom。

不用插件系统也可以:安装脚本会把技能链接到 `~/.claude/skills/lightroom-agent`,再执行

```bash
claude mcp add lightroom -- <repo>/bin/lightroom-agent mcp
```

## Claude Desktop

设置 › 开发者 › **编辑配置**,打开 `claude_desktop_config.json`,加入:

```json
{
  "mcpServers": {
    "lightroom": { "command": "<repo>/bin/lightroom-agent", "args": ["mcp"] }
  }
}
```

重启 Claude Desktop,工具会出现在 🔨 / 连接器菜单里。

## Codex(命令行、IDE 插件、Codex 应用):ChatGPT 用户看这里

ChatGPT 桌面版和网页版不能启动本地 MCP 服务,也就连不到你电脑上的 Lightroom。请用 **Codex**,用 ChatGPT 账号登录即可。

技能:安装脚本会链接到 `~/.codex/skills/lightroom-agent`。MCP(Codex 推荐用 MCP,因为它的沙箱可能拦截命令行需要的本机网络连接):
在 `~/.codex/config.toml` 加入

```toml
[mcp_servers.lightroom]
command = "<repo>/bin/lightroom-agent"
args = ["mcp"]
tool_timeout_sec = 900
```

或执行 `codex mcp add lightroom -- <repo>/bin/lightroom-agent mcp`。

## Gemini CLI

技能:`gemini skills link <repo>/skills/lightroom-agent`(安装脚本已链接 `~/.gemini/skills/lightroom-agent`)。
在仓库目录里运行 Gemini 时,仓库里的 `GEMINI.md` 也会引导它使用这个技能。
MCP:在 `~/.gemini/settings.json` 里加入

```json
{
  "mcpServers": {
    "lightroom": { "command": "<repo>/bin/lightroom-agent", "args": ["mcp"], "timeout": 900000 }
  }
}
```

## Cursor

技能:`~/.cursor/skills/lightroom-agent`(安装脚本已链接)。MCP:设置 › MCP › **Add new global MCP server**,
或在 `~/.cursor/mcp.json` 里写入和 Claude Desktop 相同的 `mcpServers` 配置。

## WorkBuddy(CodeBuddy)

技能:安装脚本已链接 `~/.workbuddy/skills/lightroom-agent`;也可以在对话里输入 **导入技能**,选择 `skills/lightroom-agent`
文件夹。MCP:设置 › MCP › 添加,粘贴上面的 `mcpServers` JSON。

## 豆包模型:用 Trae 或 Cherry Studio

豆包 App 本身不能调用本地工具。可以在下面两个应用里使用豆包模型:

- **Trae**(字节跳动的 IDE,内置豆包):技能在 `~/.trae/skills/lightroom-agent`(安装脚本已链接);MCP:设置 › MCP ›
  添加 › **手动添加**,粘贴上面的 `mcpServers` JSON。
- **Cherry Studio**:添加"火山方舟"模型服务商,选一个支持图片理解的豆包模型;然后 设置 › MCP 服务器 › 添加:
  类型 **stdio**,命令 `<repo>/bin/lightroom-agent`,参数 `mcp`。在对话框的 MCP 菜单里启用它。

## 其他 MCP 客户端

任何支持 stdio MCP 的客户端都一样配置:命令 `<repo>/bin/lightroom-agent`,参数 `mcp`。如果客户端不支持技能,
把 `skills/lightroom-agent/SKILL.md` 的内容贴到项目说明或系统提示词里,里面有完整流程和质量检查要求。

## 说明

- 第一次运行 `lightroom-agent` 会创建 Python 环境(1–3 分钟,占用约 400 MB)。
- 长任务(选片、套风格)在 MCP 服务里后台运行:AI 启动任务后用 `job_status` 查询进度。
