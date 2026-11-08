English | [中文](./releasing_CN.md)

# Releasing

Pushing a version tag publishes a GitHub release automatically
([.github/workflows/release.yml](../.github/workflows/release.yml)). Tags are plain versions **without a "v"**:
`0.3.0`, `0.4.0-beta.1`.

## Steps

1. While you work, note user-visible changes under `## Unreleased` in [CHANGELOG.md](../CHANGELOG.md).
2. Set the new version everywhere:

   ```bash
   python3 scripts/release.py 0.3.0 --dry-run   # preview
   python3 scripts/release.py 0.3.0             # edit the files (no git)
   ```

   The script sets the version in all four places that carry it (`.claude-plugin/plugin.json`, the plugin's
   `Info.lua` and `Server.lua`, `pipeline/mcp_server.py`) and turns `## Unreleased` into `## 0.3.0 - <date>`.
3. Commit, tag and push:

   ```bash
   git commit -am "release: 0.3.0"
   git tag 0.3.0
   git push origin main 0.3.0
   ```

   (`python3 scripts/release.py 0.3.0 --push` does steps 2 and 3 in one go.)
4. GitHub Actions then:
   - checks that the tag matches every version file, that Python and Lua compile and that every style parses;
   - zips the Lightroom plugin (`LightroomAgent.lrplugin-0.3.0.zip`);
   - publishes the release: the CHANGELOG section as highlights, install / update instructions, the commit list since
     the previous tag and the plugin zip.

If the version files don't match the tag, the check fails and nothing is published: delete the tag
(`git tag -d 0.3.0 && git push origin :refs/tags/0.3.0`), fix the versions, tag again.

A tag with a suffix (`0.4.0-beta.1`) becomes a pre-release. Claude Code users get the update with
`/plugin update lightroom-agent` (it compares the `version` in `plugin.json`). To re-publish an existing tag (e.g.
after editing CHANGELOG notes): Actions > Release > Run workflow > `0.3.0`.
