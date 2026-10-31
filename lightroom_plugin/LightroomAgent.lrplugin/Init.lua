-- Runs when Lightroom loads or enables the plugin: start the bridge server.
local ok, err = pcall(function()
  local Server = require 'Server'
  local LrLogger = import 'LrLogger'
  local l = LrLogger('LightroomAgent'); l:enable('logfile')
  l:trace('init script invoked')
  Server.start()
end)
if not ok then
  local LrLogger = import 'LrLogger'
  local log = LrLogger('LightroomAgent')
  log:enable('logfile')
  log:error('init failed: ' .. tostring(err))
end
