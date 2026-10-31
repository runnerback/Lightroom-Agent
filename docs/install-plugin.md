English | [中文](./install-plugin_CN.md)

# Installing the Lightroom plugin

Lightroom Agent talks to **Adobe Lightroom Classic** through a small plugin, `LightroomAgent.lrplugin`. The plugin opens
two ports on `127.0.0.1` (50111 for commands, 50112 for replies) while Lightroom is running; nothing is reachable from
other computers. Lightroom itself does all the rendering, so your edits stay normal, editable Lightroom develop
settings with their own history steps.

**Requirements:** Lightroom Classic on macOS or Windows (tested with 14.x; the plugin uses SDK 6+ features).
Lightroom (the cloud "Lightroom" app without "Classic") has no plugin system and is not supported.

## Option A — automatic (recommended)

From the cloned repository:

```bash
python3 scripts/install.py          # full setup, including the plugin
# or only the plugin:
bin/lightroom-agent install-plugin  # Windows: bin\lightroom-agent.cmd install-plugin
```

This copies the plugin into the folder Lightroom scans at start-up:

| System | Folder |
|---|---|
| macOS | `~/Library/Application Support/Adobe/Lightroom/Modules/` |
| Windows | `%APPDATA%\Adobe\Lightroom\Modules\` |

Then **quit and restart Lightroom Classic**. Plugins in this folder load automatically; you do not need the Plug-in
Manager. To update later, `git pull` and run `install-plugin` again, then restart Lightroom.

## Option B — manual, with the Plug-in Manager

Use this if you prefer to keep the plugin inside the repository (handy when you edit it).

1. In Lightroom Classic choose **File › Plug-in Manager…** (macOS ⌥⇧⌘, / Windows Ctrl+Alt+Shift+,).
2. Click **Add** (bottom left).
3. Select the folder `lightroom_plugin/LightroomAgent.lrplugin` inside the repository and click **Add Plug-in**.
4. **Lightroom Agent** appears in the list with a green dot: *Installed and running*. Click **Done**.

Lightroom remembers this path: do not move or rename the repository afterwards (if you do, repeat the steps).

> Use either A or B, not both: two copies of the plugin would compete for the same ports. If you switch, remove the
> other copy (Plug-in Manager › **Remove**, or delete it from the Modules folder) and restart Lightroom.

## Check that it works

1. In Lightroom: **Library › Plug-in Extras › Lightroom Agent: Status**. The dialog says *running* and shows the two
   ports.
2. In a terminal:

   ```bash
   lightroom-agent doctor
   ```

   The last check reads `ok   Lightroom connection: Lightroom Agent ... - catalog <your catalog>`.

The plugin starts once Lightroom's main window has finished opening a catalog. Right after launch, wait a few seconds.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `cannot connect to the command port 50111` | Lightroom Classic is not running, still starting, or the plugin is not loaded. Open **File › Plug-in Manager** and check that *Lightroom Agent* is listed and enabled. If not, install it (A or B) and restart Lightroom. |
| `handshake failed` / commands hang | **Library › Plug-in Extras › Lightroom Agent: Restart service**. Also check whether Lightroom is showing a dialog that waits for you (an export or catalog message): close it. |
| Red dot in the Plug-in Manager | Select the plugin; the error text is shown below the list. Re-install it from a fresh `git pull`. |
| Ports already in use | Another program, or a second copy of the plugin, uses 50111/50112. macOS: `lsof -nP -iTCP:50111 -iTCP:50112`; Windows: `netstat -ano \| findstr 5011`. |
| Commands interrupted during exports | In the Plug-in Manager (Option B only) untick **Reload plug-in on each export** under *Plug-in Author Tools*. |

Plugin log:
- macOS: `~/Library/Logs/Adobe/Lightroom/LrClassicLogs/LightroomAgent.log`
- Windows: `%LOCALAPPDATA%\Adobe\Lightroom\Logs\LrClassicLogs\LightroomAgent.log`

## Uninstall

Delete `LightroomAgent.lrplugin` from the Modules folder (Option A) or click **Remove** in the Plug-in Manager
(Option B), then restart Lightroom. Develop settings the agent applied stay in your catalog like any other edit; undo
them with `lightroom-agent rollback` or in Lightroom's History panel.

## What the plugin can and cannot do

| Command | What it does |
|---|---|
| `ping`, `catalog_info` | connection check; folders and collections of the open catalog |
| `list_folder`, `list_collection`, `get_selection`, `get_meta` | photos and metadata (rating, flag, label, ISO, capture time, ...) |
| `set_meta`, `add_keywords` | ratings, flags, colour labels, titles, captions, keywords |
| `collection_add`, `collection_delete` | create collections (inside a collection set) and fill them |
| `get_develop`, `apply_develop` | read and apply develop settings, different per photo, as one history step |
| `export` | render JPEGs (calibration, previews, or an export you ask for) |
| `import_photos` | add files to the catalog in place, without copying |
| `_reload` | reload `Handlers.lua` without restarting Lightroom (for developers) |

Not possible through the Lightroom SDK: AI Denoise, HDR / panorama merge, masks and other menu-only features. The agent
recommends them by name when they would help. The plugin never deletes photos and never touches crop, straighten or
orientation.

`eval` (run Lua inside Lightroom, for debugging) is off unless a file named `DEV_ENABLE_EVAL` exists in the plugin
folder. Leave it off.
