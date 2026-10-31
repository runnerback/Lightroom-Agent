[English](./install-plugin.md) | 中文

# 安装 Lightroom 插件

Lightroom Agent 通过一个小插件 `LightroomAgent.lrplugin` 和 **Adobe Lightroom Classic** 通信。Lightroom 运行时,插件只在本机
`127.0.0.1` 上打开两个端口(50111 收命令,50112 回结果),局域网里的其他电脑访问不到。渲染全部由 Lightroom 自己完成,
所以 AI 做的调整都是普通的、可继续编辑的修改照片参数,并带有自己的历史记录步骤。

**要求:** macOS 或 Windows 上的 Lightroom Classic(在 14.x 上测试;插件只用到 SDK 6 以上的功能)。
不带 "Classic" 的云端版 Lightroom 没有插件系统,不支持。

## 方式 A:自动安装(推荐)

在克隆下来的仓库目录里执行:

```bash
python3 scripts/install.py          # 完整安装,包含插件
# 或者只装插件:
bin/lightroom-agent install-plugin  # Windows:bin\lightroom-agent.cmd install-plugin
```

插件会被复制到 Lightroom 启动时自动扫描的文件夹:

| 系统 | 文件夹 |
|---|---|
| macOS | `~/Library/Application Support/Adobe/Lightroom/Modules/` |
| Windows | `%APPDATA%\Adobe\Lightroom\Modules\` |

然后**退出并重新打开 Lightroom Classic**。这个文件夹里的插件会自动加载,不需要再去增效工具管理器里添加。
以后更新:`git pull` 后再运行一次 `install-plugin`,重启 Lightroom。

## 方式 B:手动,用增效工具管理器添加

想让插件留在仓库里(比如你要改插件代码)时用这种方式。

1. Lightroom Classic 菜单 **文件 › 增效工具管理器…**(macOS ⌥⇧⌘, / Windows Ctrl+Alt+Shift+,)。
2. 点左下角 **添加**。
3. 选中仓库里的 `lightroom_plugin/LightroomAgent.lrplugin` 文件夹,点 **添加增效工具**。
4. 左侧列表出现 **Lightroom Agent**,绿色圆点表示"已安装并正在运行"。点 **完成**。

Lightroom 记住的是这个路径:之后不要移动或重命名仓库目录(如果移动了,重新做一遍上面的步骤)。

> A 和 B 二选一,不要同时用:两份插件会抢同一组端口。要换方式时,先删掉另一份(增效工具管理器里点 **移去**,
> 或从 Modules 文件夹删除),再重启 Lightroom。

## 检查是否装好

1. Lightroom 菜单 **图库 › 增效工具附加功能 › Lightroom Agent: Status**,弹窗显示 running 和两个端口。
2. 终端里运行:

   ```bash
   lightroom-agent doctor
   ```

   最后一项显示 `ok   Lightroom connection: Lightroom Agent ... - catalog <你的目录库>` 即成功。

插件在 Lightroom 主窗口打开目录库之后才启动,刚启动 Lightroom 时请稍等几秒。

## 常见问题

| 现象 | 处理 |
|---|---|
| `cannot connect to the command port 50111` | Lightroom Classic 没开、还在启动,或插件没加载。打开 **文件 › 增效工具管理器**,确认列表里有 *Lightroom Agent* 且已启用;没有就按 A 或 B 安装后重启 Lightroom。 |
| `handshake failed` / 命令一直不返回 | 菜单 **图库 › 增效工具附加功能 › Lightroom Agent: Restart service**。也看一下 Lightroom 是否弹出了等你确认的对话框(导出提示、目录库提示等),关掉它。 |
| 增效工具管理器里是红点 | 选中插件,列表下方会显示具体错误。`git pull` 后重新安装。 |
| 端口被占用 | 别的程序或第二份插件占用了 50111/50112。macOS:`lsof -nP -iTCP:50111 -iTCP:50112`;Windows:`netstat -ano \| findstr 5011`。 |
| 导出时命令被打断 | (仅方式 B)在增效工具管理器的"增效工具作者工具"里取消勾选 **每次导出时重新载入增效工具**。 |

插件日志:
- macOS:`~/Library/Logs/Adobe/Lightroom/LrClassicLogs/LightroomAgent.log`
- Windows:`%LOCALAPPDATA%\Adobe\Lightroom\Logs\LrClassicLogs\LightroomAgent.log`

## 卸载

方式 A:从 Modules 文件夹删除 `LightroomAgent.lrplugin`;方式 B:增效工具管理器里点 **移去**。然后重启 Lightroom。
AI 已经应用的修改参数和其他修改一样保留在目录库里,可以用 `lightroom-agent rollback` 或 Lightroom 的历史记录面板撤销。

## 插件能做什么、不能做什么

| 命令 | 作用 |
|---|---|
| `ping`、`catalog_info` | 连接检查;当前目录库的文件夹和收藏集 |
| `list_folder`、`list_collection`、`get_selection`、`get_meta` | 照片列表和元数据(星级、旗标、色标、ISO、拍摄时间等) |
| `set_meta`、`add_keywords` | 星级、旗标、色标、标题、说明、关键字 |
| `collection_add`、`collection_delete` | 在收藏集组里新建收藏集并放入照片 |
| `get_develop`、`apply_develop` | 读取和应用修改照片参数,每张可以不同,作为一步历史记录 |
| `export` | 渲染 JPEG(校准用图、预览图,或你要求的导出) |
| `import_photos` | 把文件原地添加到目录库,不复制 |
| `_reload` | 不重启 Lightroom 重新加载 `Handlers.lua`(开发用) |

Lightroom SDK 做不到的:AI 降噪、HDR / 全景合并、蒙版等只能在菜单里操作的功能。需要时 AI 会告诉你用哪个功能。
插件不会删除照片,也不会改动裁剪、拉直和方向。

`eval`(在 Lightroom 里执行 Lua,调试用)默认关闭,只有插件文件夹里存在名为 `DEV_ENABLE_EVAL` 的文件时才启用。请保持关闭。
