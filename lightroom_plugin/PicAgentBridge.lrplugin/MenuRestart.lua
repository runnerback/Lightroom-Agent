local LrDialogs = import 'LrDialogs'
local LrTasks = import 'LrTasks'
LrTasks.startAsyncTask(function()
  local ok, Server = pcall(require, 'Server')
  if not ok then
    LrDialogs.message('Pic Agent Bridge', '加载失败: ' .. tostring(Server), 'critical')
    return
  end
  Server.stop()
  LrTasks.sleep(1.0)
  Server.start()
  LrTasks.sleep(0.5)
  LrDialogs.message('Pic Agent Bridge', Server.statusText(), 'info')
end)
