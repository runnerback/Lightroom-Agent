-- Runs when Lightroom loads or enables the plugin: start the bridge server.
local ok, err = pcall(function()
  local Server = require 'Server'
  Server.start()
end)
if not ok then
  local LrLogger = import 'LrLogger'
  local log = LrLogger('PicAgentBridge')
  log:enable('logfile')
  log:error('init failed: ' .. tostring(err))
end
