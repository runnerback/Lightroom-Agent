[English](./releasing.md) | 中文

# 发布新版本

推送版本 tag 后,GitHub 会自动发布 Release([.github/workflows/release.yml](../.github/workflows/release.yml))。
tag 直接写版本号,**不带 "v"**:`0.3.0`、`0.4.0-beta.1`。

## 步骤

1. 平时把用户能感知的改动记在 [CHANGELOG.md](../CHANGELOG.md) 的 `## Unreleased` 下面。
2. 统一修改版本号:

   ```bash
   python3 scripts/release.py 0.3.0 --dry-run   # 预览
   python3 scripts/release.py 0.3.0             # 修改文件(不做 git 操作)
   ```

   脚本会同时修改 4 处版本号(`.claude-plugin/plugin.json`、插件的 `Info.lua` 和 `Server.lua`、
   `pipeline/mcp_server.py`),并把 `## Unreleased` 改成 `## 0.3.0 - <日期>`。
3. 提交、打 tag、推送:

   ```bash
   git commit -am "release: 0.3.0"
   git tag 0.3.0
   git push origin main 0.3.0
   ```

   (`python3 scripts/release.py 0.3.0 --push` 可以一次完成第 2、3 步。)
4. 接下来 GitHub Actions 会:
   - 检查 tag 和所有版本号一致,Python、Lua 能编译,每个风格文件都能解析;
   - 打包 Lightroom 插件(`LightroomAgent.lrplugin-0.3.0.zip`);
   - 发布 Release:CHANGELOG 对应段落作为亮点,附安装/更新说明、上个版本以来的提交列表和插件 zip。

如果版本号文件和 tag 不一致,检查不通过,不会发布:先删掉 tag
(`git tag -d 0.3.0 && git push origin :refs/tags/0.3.0`),改好版本号,再重新打 tag。

带后缀的 tag(`0.4.0-beta.1`)会发布为预发布版本。Claude Code 用户执行 `/plugin update lightroom-agent` 即可更新
(它比较的是 `plugin.json` 里的 `version`)。重新发布已有的 tag(比如改了 CHANGELOG 说明):
Actions > Release > Run workflow > 填 `0.3.0`。
