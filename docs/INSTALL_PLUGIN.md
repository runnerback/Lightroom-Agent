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

**文件 › 增效工具管理器…** › 选中 Pic Agent Bridge › 右侧"增效工具作者工具"区域点 **重新加载增效工具**,
然后 **图库 › 增效工具附加功能 › Pic Agent Bridge: 重启服务**。

## 排错

- 日志文件:`~/Documents/LrClassicLogs/PicAgentBridge.log`
- 端口被占用:`lsof -nP -iTCP:50111 -iTCP:50112`
- 插件状态为红色:在增效工具管理器里选中插件,下方会显示具体错误信息。

## 插件能做什么

| 命令 | 作用 |
|---|---|
| ping / catalog_info | 连通性、目录库文件夹树 |
| list_folder / list_collection / get_selection | 读取照片及元数据(星级、旗标、色标、ISO、快门等) |
| set_meta | 批量设置星级、旗标、色标、标题、说明 |
| add_keywords | 批量加关键字 |
| collection_add | 建收藏集并放入照片 |
| select / show_folder / show_collection | 控制 Lightroom 界面当前显示与选中 |
| get_develop / apply_develop | 读取与批量应用修图参数(每张可不同) |
| export | 按路径、收藏集、文件夹或筛选条件导出到指定目录 |

做不到:AI 降噪、HDR/全景合并等菜单功能,需在 Lightroom 内手动执行。
