-- Runs when Lightroom quits or the plugin is disabled: stop the bridge server.
local okReq, Server = pcall(require, 'Server')
if okReq and Server then pcall(Server.stop, 'shutdown/disable script') end
return {
  LrShutdownFunction = function(doneFunction, progressFunction)
    if okReq and Server then pcall(Server.stop, 'LrShutdownFunction') end
    doneFunction()
  end,
}
