# Pic Agent Bridge 插件安装(Lightroom Classic 14,macOS)

插件目录(请勿移动,Lightroom 直接引用这个路径):

```
/Volumes/T4/Projects/pic_agent_lightroom/lightroom_plugin/PicAgentBridge.lrplugin
```

## 安装步骤

1. 打开 Lightroom Classic,菜单 **文件 › 增效工具管理器…**(快捷键 ⌥⇧⌘,)。
2. 点左下角 **添加**。
3. 在文件对话框里定位到上面的目录,选中 `PicAgentBridge.lrplugin`,点 **添加增效工具**。
4. 左侧列表出现 **Pic Agent Bridge**,状态为绿色圆点"已安装并正在运行"。点 **完成**。
5. 验证:菜单 **图库 › 增效工具附加功能 › Pic Agent Bridge: 状态**,弹窗应显示"运行中",命令端口 50111,响应端口 50112。

安装后插件随 Lightroom 自动启动,不需要每次手动操作。

## 终端验证

```bash
python3 /Volumes/T4/Projects/pic_agent_lightroom/bridge/lr_client.py ping
```

返回 `"pong": true` 和目录库路径即为成功。

## 更新插件代码后

改动 `Handlers.lua` 时只需在终端执行 `python3 bridge/lr_client.py reload`,无需动 Lightroom。改动 `Server.lua` 等其他文件时:

**文件 › 增效工具管理器…** › 选中 Pic Agent Bridge › 右侧"增效工具作者工具"区域点 **重新加载增效工具**。
新实例会自动让旧实例退出并接管端口(约 2 秒)。如果状态弹窗里的 gen 编号没有变化,就退出并重新打开 Lightroom。

## 使用约束

- 增效工具管理器里的 **“每次导出时重新载入增效工具”** 必须取消勾选,否则导出时插件会被重新载入,正在进行的桥接任务会被打断。

- **同一时间只能有一个客户端**。`lr_client.py` 内置文件锁,多个脚本并发调用会自动排队,不要绕过它。
- 每次调用会先用 ping 握手确认响应通道属于自己,握手失败会给出明确提示。
- 插件处理命令是串行的,导出等长任务期间其他命令会排队等待。

## 排错

- 日志文件:`~/Library/Logs/Adobe/Lightroom/LrClassicLogs/PicAgentBridge.log`
- 端口被占用:`lsof -nP -iTCP:50111 -iTCP:50112`
- 插件状态为红色:在增效工具管理器里选中插件,下方会显示具体错误信息。

## 插件能做什么

| 命令 | 作用 |
|---|---|
| ping / _status / catalog_info | 连通性、服务状态、目录库文件夹树 |
| list_folder / list_collection / get_selection / get_meta | 读取照片及元数据(星级、旗标、色标、ISO、快门等) |
| set_meta | 批量设置星级、旗标、色标、标题、说明 |
| add_keywords | 批量加关键字 |
| collection_add / collection_delete | 建收藏集并放入照片,删除收藏集 |
| select / show_folder / show_collection | 控制 Lightroom 界面当前显示与选中 |
| get_develop / apply_develop | 读取与批量应用修图参数(每张可不同) |
| export | 按路径、收藏集、文件夹或筛选条件导出到指定目录 |
| _reload / eval | 热重载 Handlers.lua;在 Lightroom 内执行一段 Lua 做诊断 |

做不到:AI 降噪、HDR/全景合并等菜单功能,需在 Lightroom 内手动执行。
