English | [中文](./releasing_CN.md)

# Releasing

Pushing a version tag publishes a GitHub release automatically
([.github/workflows/release.yml](../.github/workflows/release.yml)).

## Steps

1. While you work, note user-visible changes under `## Unreleased` in [CHANGELOG.md](../CHANGELOG.md).
2. Commit everything, then:

   ```bash
   python3 scripts/release.py 0.2.0 --dry-run   # preview
   python3 scripts/release.py 0.2.0 --push      # bump, commit "release: v0.2.0", tag v0.2.0, push both
   ```

   The script sets the version in all four places that carry it (`.claude-plugin/plugin.json`, the plugin's
   `Info.lua` and `Server.lua`, `pipeline/mcp_server.py`) and turns `## Unreleased` into `## v0.2.0 - <date>`.
3. GitHub Actions then:
   - checks that the tag matches every version file, that Python and Lua compile and that every style parses;
   - zips the Lightroom plugin (`LightroomAgent.lrplugin-v0.2.0.zip`);
   - publishes the release: the CHANGELOG section as highlights, install / update instructions, the commit list since
     the previous tag and the plugin zip.

A tag with a suffix (`v0.3.0-beta.1`) becomes a pre-release. Claude Code users get the update with
`/plugin update lightroom-agent` (it compares the `version` in `plugin.json`).

## By hand

`git tag -a v0.2.0 -m v0.2.0 && git push origin v0.2.0` works too, as long as the version files already say 0.2.0;
otherwise the check fails and nothing is published. To re-publish an existing tag (e.g. after editing CHANGELOG
notes): Actions > Release > Run workflow > `v0.2.0`.
