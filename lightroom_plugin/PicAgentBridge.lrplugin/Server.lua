-- Server.lua : local TCP bridge between Lightroom Classic and the Pic Agent scripts.
-- Commands arrive on PORT_IN (one JSON object per line); responses go out on PORT_OUT.
local LrSocket = import 'LrSocket'
local LrTasks = import 'LrTasks'
local LrFunctionContext = import 'LrFunctionContext'
local LrLogger = import 'LrLogger'
local LrDate = import 'LrDate'

local json = require 'json'

local log = LrLogger('PicAgentBridge')
log:enable('logfile')

local M = {
  VERSION = '0.1.0',
  PORT_IN = 50111,
  PORT_OUT = 50112,
  running = false,
  queue = {},
  pending = {},
  sendSocket = nil,
  sendConnected = false,
  cmdConnected = false,
  startedAt = nil,
  stats = { received = 0, handled = 0, errors = 0 },
}

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

function M.respond(tbl)
  local ok, s = pcall(json.encode, tbl)
  if not ok then
    s = json.encode({ id = tbl.id, ok = false, error = 'response encode failed: ' .. tostring(s) })
  end
  M.pending[#M.pending + 1] = s .. '\n'
  flushPending()
end

local function handleOne(raw)
  local okH, Handlers = pcall(require, 'Handlers')
  if not okH then
    M.respond({ ok = false, error = 'Handlers.lua failed to load: ' .. tostring(Handlers) })
    return
  end
  local ok, req = pcall(json.decode, raw)
  if not ok or type(req) ~= 'table' then
    M.respond({ ok = false, error = 'bad request json: ' .. tostring(req) })
    return
  end
  local id, cmd = req.id, req.cmd
  local fn = nil
  if type(cmd) == 'string' and cmd:sub(1, 1) ~= '_' then fn = Handlers[cmd] end
  if type(fn) ~= 'function' then
    M.respond({ id = id, ok = false, error = 'unknown command: ' .. tostring(cmd) })
    return
  end
  local t0 = LrDate.currentTime()
  local ok2, result = LrTasks.pcall(fn, req.params or {}, M)
  local elapsed = LrDate.currentTime() - t0
  if ok2 then
    M.respond({ id = id, ok = true, result = result, elapsed = elapsed })
  else
    M.stats.errors = M.stats.errors + 1
    log:warn(string.format('command %s failed: %s', tostring(cmd), tostring(result)))
    M.respond({ id = id, ok = false, error = tostring(result), elapsed = elapsed })
  end
end

function M.start()
  if M.running then return false end
  M.running = true
  M.startedAt = LrDate.currentTime()
  LrTasks.startAsyncTask(function()
    LrFunctionContext.callWithContext('PicAgentBridgeServer', function(context)
      local recv = LrSocket.bind {
        functionContext = context,
        plugin = _PLUGIN,
        port = M.PORT_IN,
        mode = 'receive',
        onConnecting = function() end,
        onConnected = function()
          M.cmdConnected = true
          log:trace('command client connected')
        end,
        onMessage = function(_, msg)
          if type(msg) == 'string' and #msg > 0 then
            M.stats.received = M.stats.received + 1
            M.queue[#M.queue + 1] = msg
          end
        end,
        onClosed = function(s)
          M.cmdConnected = false
          if M.running then s:reconnect() end
        end,
        onError = function(s, err)
          M.cmdConnected = false
          log:warn('command socket error: ' .. tostring(err))
          if M.running and err == 'timeout' then s:reconnect() end
        end,
      }
      local send = LrSocket.bind {
        functionContext = context,
        plugin = _PLUGIN,
        port = M.PORT_OUT,
        mode = 'send',
        onConnecting = function() end,
        onConnected = function()
          M.sendConnected = true
          log:trace('response client connected')
          flushPending()
        end,
        onMessage = function() end,
        onClosed = function(s)
          M.sendConnected = false
          if M.running then s:reconnect() end
        end,
        onError = function(s, err)
          M.sendConnected = false
          log:warn('response socket error: ' .. tostring(err))
          if M.running and err == 'timeout' then s:reconnect() end
        end,
      }
      M.sendSocket = send
      log:trace(string.format('bridge %s listening: in=%d out=%d', M.VERSION, M.PORT_IN, M.PORT_OUT))
      while M.running do
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
      pcall(send.close, send)
      M.sendSocket = nil
      M.sendConnected = false
      M.cmdConnected = false
      log:trace('bridge stopped')
    end)
  end)
  return true
end

function M.stop()
  M.running = false
end

function M.statusText()
  local up = M.startedAt and (LrDate.currentTime() - M.startedAt) or 0
  return string.format(
    'Pic Agent Bridge %s\n状态: %s\n命令端口 %d: %s\n响应端口 %d: %s\n已接收 %d / 已处理 %d / 失败 %d\n运行 %d 秒\n日志: ~/Documents/LrClassicLogs/PicAgentBridge.log',
    M.VERSION, M.running and '运行中' or '已停止',
    M.PORT_IN, M.cmdConnected and '客户端已连接' or '等待连接',
    M.PORT_OUT, M.sendConnected and '客户端已连接' or '等待连接',
    M.stats.received, M.stats.handled, M.stats.errors, up)
end

return M
