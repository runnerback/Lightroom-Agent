-- Runs when Lightroom loads or enables the plugin: start the bridge server.
local ok, err = pcall(function()
  local Server = require 'Server'
  local LrLogger = import 'LrLogger'
  local l = LrLogger('PicAgentBridge'); l:enable('logfile')
  l:trace('init script invoked')
  Server.start()
end)
if not ok then
  local LrLogger = import 'LrLogger'
  local log = LrLogger('PicAgentBridge')
  log:enable('logfile')
  log:error('init failed: ' .. tostring(err))
end
