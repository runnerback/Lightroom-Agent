local LrDialogs = import 'LrDialogs'
local LrTasks = import 'LrTasks'
LrTasks.startAsyncTask(function()
  local ok, Server = pcall(require, 'Server')
  if not ok then
    LrDialogs.message('Lightroom Agent', 'Failed to load: ' .. tostring(Server), 'critical')
    return
  end
  LrDialogs.message('Lightroom Agent', Server.statusText(), 'info')
end)
