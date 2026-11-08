[English](./releasing.md) | 中文

# 发布新版本

推送版本 tag 后,GitHub 会自动发布 Release([.github/workflows/release.yml](../.github/workflows/release.yml))。

## 步骤

1. 平时把用户能感知的改动记在 [CHANGELOG.md](../CHANGELOG.md) 的 `## Unreleased` 下面。
2. 提交所有改动后执行:

   ```bash
   python3 scripts/release.py 0.2.0 --dry-run   # 预览
   python3 scripts/release.py 0.2.0 --push      # 改版本号、提交 "release: v0.2.0"、打 tag v0.2.0、推送
   ```

   脚本会同时修改 4 处版本号(`.claude-plugin/plugin.json`、插件的 `Info.lua` 和 `Server.lua`、
   `pipeline/mcp_server.py`),并把 `## Unreleased` 改成 `## v0.2.0 - <日期>`。
3. 接下来 GitHub Actions 会:
   - 检查 tag 和所有版本号一致,Python、Lua 能编译,每个风格文件都能解析;
   - 打包 Lightroom 插件(`LightroomAgent.lrplugin-v0.2.0.zip`);
   - 发布 Release:CHANGELOG 对应段落作为亮点,附安装/更新说明、上个版本以来的提交列表和插件 zip。

带后缀的 tag(`v0.3.0-beta.1`)会发布为预发布版本。Claude Code 用户执行 `/plugin update lightroom-agent` 即可更新
(它比较的是 `plugin.json` 里的 `version`)。

## 手动打 tag

`git tag -a v0.2.0 -m v0.2.0 && git push origin v0.2.0` 也可以,但前提是版本号文件已经是 0.2.0,否则检查不通过,
不会发布。重新发布已有的 tag(比如改了 CHANGELOG 说明):Actions > Release > Run workflow > 填 `v0.2.0`。
