local LrDialogs = import 'LrDialogs'
local LrTasks = import 'LrTasks'
LrTasks.startAsyncTask(function()
  local ok, Server = pcall(require, 'Server')
  if not ok then
    LrDialogs.message('Pic Agent Bridge', '加载失败: ' .. tostring(Server), 'critical')
    return
  end
  LrDialogs.message('Pic Agent Bridge', Server.statusText(), 'info')
end)
