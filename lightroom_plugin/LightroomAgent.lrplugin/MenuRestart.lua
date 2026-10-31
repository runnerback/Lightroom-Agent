local LrDialogs = import 'LrDialogs'
local LrTasks = import 'LrTasks'
LrTasks.startAsyncTask(function()
  local ok, Server = pcall(require, 'Server')
  if not ok then
    LrDialogs.message('Lightroom Agent', 'Failed to load: ' .. tostring(Server), 'critical')
    return
  end
  Server.stop('menu restart')
  LrTasks.sleep(1.0)
  Server.start()
  LrTasks.sleep(0.5)
  LrDialogs.message('Lightroom Agent', Server.statusText(), 'info')
end)
