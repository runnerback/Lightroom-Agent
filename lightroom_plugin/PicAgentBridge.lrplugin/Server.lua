-- Server.lua : local TCP bridge between Lightroom Classic and the Pic Agent scripts.
-- Commands arrive on PORT_IN (one JSON object per line); responses go out on PORT_OUT.
--
-- Protocol notes (learned the hard way):
--  * One client at a time. The client connects PORT_IN first, then PORT_OUT.
--  * LrSocket never reports a closed peer on a "send" socket, and reconnect() on a connected
--    send socket tears the whole context down. So on every client arrival/departure we close the
--    send socket and bind a brand-new one (the approach MIDI2LR uses).
--  * While listening with no client, LrSocket raises 'timeout' every ~10 s; we must call
--    reconnect() then to keep listening (normal, not an error). Never gate that on socket identity:
--    the object handed to callbacks is not the one bind() returned.
--  * A plugin reload leaves the old async task alive; a generation counter in LrPrefs lets the old
--    instance notice and shut itself down.
--  * Handlers.lua can be hot-reloaded with the "_reload" command (no Lightroom reload needed).
local LrSocket = import 'LrSocket'
local LrTasks = import 'LrTasks'
local LrFunctionContext = import 'LrFunctionContext'
local LrLogger = import 'LrLogger'
local LrDate = import 'LrDate'
local LrPrefs = import 'LrPrefs'
local LrPathUtils = import 'LrPathUtils'

local json = require 'json'

local log = LrLogger('PicAgentBridge')
log:enable('logfile')

local prefs = LrPrefs.prefsForPlugin()

local M = {
  VERSION = '0.2.2',
  PORT_IN = 50111,
  PORT_OUT = 50112,
  running = false,
  generation = 0,
  queue = {},
  pending = {},
  sendSocket = nil,
  sendState = nil,
  context = nil,
  sendConnected = false,
  cmdConnected = false,
  startedAt = nil,
  stats = { received = 0, handled = 0, errors = 0 },
}

---------------------------------------------------------------- handlers (hot-reloadable)

local HandlersRef = nil

local function getHandlers()
  if HandlersRef then return HandlersRef end
  local ok, H = pcall(require, 'Handlers')
  if ok and type(H) == 'table' then
    HandlersRef = H
    return H
  end
  return nil, H
end

function M.reloadHandlers()
  local path = LrPathUtils.child(_PLUGIN.path, 'Handlers.lua')
  local lf = loadfile
  if not lf then error('loadfile is not available in this Lua environment') end
  local chunk, err = lf(path)
  if not chunk then error('Handlers.lua compile failed: ' .. tostring(err)) end
  local ok, H = pcall(chunk)
  if not ok then error('Handlers.lua load failed: ' .. tostring(H)) end
  if type(H) ~= 'table' then error('Handlers.lua did not return a table') end
  HandlersRef = H
  log:trace('Handlers.lua hot-reloaded')
  return true
end

---------------------------------------------------------------- sockets

local function flushPending()
  if not (M.sendConnected and M.sendSocket) then return end
  while #M.pending > 0 do
    local m = table.remove(M.pending, 1)
    local ok, err = pcall(M.sendSocket.send, M.sendSocket, m)
    if not ok then
      log:warn('send failed: ' .. tostring(err))
      table.insert(M.pending, 1, m)
      M.sendConnected = false
      return
    end
  end
end

-- Wrap socket callbacks so an error inside one is logged instead of killing the function context.
local function safe(name, fn)
  return function(...)
    local ok, err = pcall(fn, ...)
    if not ok then log:error(name .. ' callback failed: ' .. tostring(err)) end
  end
end

-- Bind a fresh "send" socket on the response port.
local function bindSend(context)
  local state = { closed = false }
  local s = LrSocket.bind {
    functionContext = context,
    plugin = _PLUGIN,
    port = M.PORT_OUT,
    mode = 'send',
    onConnecting = function() log:trace('response port listening') end,
    onConnected = safe('send.onConnected', function()
      if state.closed then return end
      M.sendConnected = true
      log:trace('response client connected')
      flushPending()
    end),
    onMessage = function() end,
    onClosed = safe('send.onClosed', function()
      if state.closed then return end
      M.sendConnected = false
      log:trace('response client disconnected')
    end),
    onError = safe('send.onError', function(sock, err)
      if state.closed then return end
      M.sendConnected = false
      if err ~= 'timeout' then log:warn('response socket error: ' .. tostring(err)) end
      if M.running then pcall(sock.reconnect, sock) end
    end),
  }
  M.sendSocket = s
  M.sendState = state
  return s
end

-- Close the current send socket (whatever state it is in) and bind a brand-new one.
local function cycleSend(reason)
  if not M.running or not M.context then return end
  log:trace('cycling response socket (' .. reason .. ')')
  M.pending = {}
  M.sendConnected = false
  local old, oldState = M.sendSocket, M.sendState
  M.sendSocket, M.sendState = nil, nil
  if oldState then oldState.closed = true end
  if old then pcall(old.close, old) end
  local ok, err = pcall(bindSend, M.context)
  if not ok then log:error('rebinding response socket failed: ' .. tostring(err)) end
end

---------------------------------------------------------------- request handling

function M.respond(tbl)
  local ok, s = pcall(json.encode, tbl)
  if not ok then
    s = json.encode({ id = tbl.id, ok = false, error = 'response encode failed: ' .. tostring(s) })
  end
  M.pending[#M.pending + 1] = s .. '\n'
  flushPending()
  return #s
end

local builtins = {}
function builtins._reload() return { reloaded = M.reloadHandlers() } end
function builtins._status()
  return { version = M.VERSION, generation = M.generation, stats = M.stats, running = M.running,
           cmdConnected = M.cmdConnected, sendConnected = M.sendConnected }
end

local function handleOne(raw)
  local ok, req = pcall(json.decode, raw)
  if not ok or type(req) ~= 'table' then
    M.respond({ ok = false, error = 'bad request json: ' .. tostring(req) })
    return
  end
  local id, cmd = req.id, req.cmd
  local fn = nil
  if type(cmd) == 'string' then
    if cmd:sub(1, 1) == '_' then
      fn = builtins[cmd]
    else
      local H, herr = getHandlers()
      if not H then
        M.respond({ id = id, ok = false, error = 'Handlers.lua failed to load: ' .. tostring(herr) })
        return
      end
      fn = H[cmd]
    end
  end
  if type(fn) ~= 'function' then
    M.respond({ id = id, ok = false, error = 'unknown command: ' .. tostring(cmd) })
    return
  end
  local t0 = LrDate.currentTime()
  local ok2, result = LrTasks.pcall(fn, req.params or {}, M)
  local elapsed = LrDate.currentTime() - t0
  if ok2 then
    local bytes = M.respond({ id = id, ok = true, result = result, elapsed = elapsed })
    log:trace(string.format('%s ok in %.2fs, %d bytes', tostring(cmd), elapsed, bytes))
  else
    M.stats.errors = M.stats.errors + 1
    log:warn(string.format('%s failed in %.2fs: %s', tostring(cmd), elapsed, tostring(result)))
    M.respond({ id = id, ok = false, error = tostring(result), elapsed = elapsed })
  end
end

---------------------------------------------------------------- lifecycle

function M.start()
  if M.running then return false end
  M.running = true
  M.startedAt = LrDate.currentTime()
  local hadPrevious = (prefs.generation or 0) > 0
  prefs.generation = (prefs.generation or 0) + 1
  M.generation = prefs.generation

  LrTasks.startAsyncTask(function()
    LrFunctionContext.callWithContext('PicAgentBridgeServer', function(context)
      -- give an older instance (plugin reload) time to notice the new generation and close its ports
      if hadPrevious then LrTasks.sleep(1.5) end

      M.context = context
      context:addFailureHandler(function(status, msg)
        log:error('server context failed: ' .. tostring(msg))
      end)
      context:addCleanupHandler(function()
        log:trace('server context cleanup (gen ' .. M.generation .. ')')
        M.running = false
        M.sendSocket = nil
        M.sendConnected = false
        M.cmdConnected = false
      end)

      local recv = LrSocket.bind {
        functionContext = context,
        plugin = _PLUGIN,
        port = M.PORT_IN,
        mode = 'receive',
        onConnecting = function() end,
        onConnected = safe('recv.onConnected', function()
          M.cmdConnected = true
          log:trace('command client connected')
          cycleSend('new command client')
        end),
        onMessage = safe('recv.onMessage', function(_, msg)
          if type(msg) == 'string' and #msg > 0 then
            M.stats.received = M.stats.received + 1
            M.queue[#M.queue + 1] = msg
          end
        end),
        onClosed = safe('recv.onClosed', function(sock)
          M.cmdConnected = false
          log:trace('command client disconnected')
          if M.running then pcall(sock.reconnect, sock) end
          cycleSend('command client left')
        end),
        onError = safe('recv.onError', function(sock, err)
          M.cmdConnected = false
          if err ~= 'timeout' then log:warn('command socket error: ' .. tostring(err)) end
          if M.running then pcall(sock.reconnect, sock) end
        end),
      }
      bindSend(context)
      log:trace(string.format('bridge %s gen %d listening: in=%d out=%d', M.VERSION, M.generation, M.PORT_IN, M.PORT_OUT))

      local ticks = 0
      while M.running do
        ticks = ticks + 1
        if ticks % 20 == 0 and prefs.generation ~= M.generation then
          log:trace(string.format('generation %d superseded by %d, stopping', M.generation, prefs.generation or -1))
          M.running = false
          break
        end
        if #M.queue > 0 then
          local raw = table.remove(M.queue, 1)
          local okLoop, errLoop = LrTasks.pcall(handleOne, raw)
          if not okLoop then log:error('handler crashed: ' .. tostring(errLoop)) end
          M.stats.handled = M.stats.handled + 1
        else
          LrTasks.sleep(0.05)
        end
      end
      pcall(recv.close, recv)
      if M.sendState then M.sendState.closed = true end
      if M.sendSocket then pcall(M.sendSocket.close, M.sendSocket) end
      M.sendSocket = nil
      M.sendConnected = false
      M.cmdConnected = false
      log:trace('bridge gen ' .. M.generation .. ' stopped')
    end)
  end)
  return true
end

function M.stop(reason)
  log:trace('stop requested (' .. tostring(reason or 'unknown') .. ') for gen ' .. tostring(M.generation))
  M.running = false
end

function M.statusText()
  local up = M.startedAt and (LrDate.currentTime() - M.startedAt) or 0
  return string.format(
    'Pic Agent Bridge %s (gen %d)\n状态: %s\n命令端口 %d: %s\n响应端口 %d: %s\n已接收 %d / 已处理 %d / 失败 %d\n运行 %d 秒\n日志: ~/Library/Logs/Adobe/Lightroom/LrClassicLogs/PicAgentBridge.log',
    M.VERSION, M.generation, M.running and '运行中' or '已停止',
    M.PORT_IN, M.cmdConnected and '客户端已连接' or '等待连接',
    M.PORT_OUT, M.sendConnected and '客户端已连接' or '等待连接',
    M.stats.received, M.stats.handled, M.stats.errors, up)
end

return M
