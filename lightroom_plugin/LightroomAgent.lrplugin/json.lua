-- json.lua : minimal JSON encode/decode for Lightroom's Lua 5.1 (no external deps)
local json = {}

json.null = setmetatable({}, { __tostring = function() return 'null' end })

local function setType(t, kind) return setmetatable(t, { __jsontype = kind }) end
function json.array(t) return setType(t or {}, 'array') end
function json.object(t) return setType(t or {}, 'object') end

local function isArray(t)
  local mt = getmetatable(t)
  if mt and mt.__jsontype then return mt.__jsontype == 'array' end
  local n = 0
  for k in pairs(t) do
    if type(k) ~= 'number' then return false end
    n = n + 1
  end
  return n == #t
end

local escapes = {
  ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b', ['\f'] = '\\f',
  ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t',
}

local function encodeString(s)
  local out = s:gsub('[%c"\\]', function(c)
    return escapes[c] or string.format('\\u%04x', c:byte())
  end)
  return '"' .. out .. '"'
end

local function encodeNumber(n)
  if n ~= n or n == math.huge or n == -math.huge then return 'null' end
  if math.floor(n) == n and math.abs(n) < 1e15 then return string.format('%d', n) end
  return string.format('%.14g', n)
end

local encodeValue
encodeValue = function(v, buf, depth)
  local tv = type(v)
  if v == nil or v == json.null then
    buf[#buf + 1] = 'null'
  elseif tv == 'boolean' then
    buf[#buf + 1] = v and 'true' or 'false'
  elseif tv == 'number' then
    buf[#buf + 1] = encodeNumber(v)
  elseif tv == 'string' then
    buf[#buf + 1] = encodeString(v)
  elseif tv == 'table' then
    if depth > 64 then error('json: nesting too deep') end
    if isArray(v) then
      buf[#buf + 1] = '['
      for i = 1, #v do
        if i > 1 then buf[#buf + 1] = ',' end
        encodeValue(v[i], buf, depth + 1)
      end
      buf[#buf + 1] = ']'
    else
      buf[#buf + 1] = '{'
      local first = true
      for k, val in pairs(v) do
        if not first then buf[#buf + 1] = ',' end
        first = false
        buf[#buf + 1] = encodeString(tostring(k))
        buf[#buf + 1] = ':'
        encodeValue(val, buf, depth + 1)
      end
      buf[#buf + 1] = '}'
    end
  else
    buf[#buf + 1] = encodeString(tostring(v))
  end
end

function json.encode(v)
  local buf = {}
  encodeValue(v, buf, 0)
  return table.concat(buf)
end

local function utf8char(cp)
  if cp < 0x80 then
    return string.char(cp)
  elseif cp < 0x800 then
    return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + cp % 0x40)
  elseif cp < 0x10000 then
    return string.char(0xE0 + math.floor(cp / 0x1000), 0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
  else
    return string.char(0xF0 + math.floor(cp / 0x40000), 0x80 + math.floor(cp / 0x1000) % 0x40,
      0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
  end
end

local simpleEscapes = { b = '\b', f = '\f', n = '\n', r = '\r', t = '\t', ['"'] = '"', ['\\'] = '\\', ['/'] = '/' }

function json.decode(str)
  if type(str) ~= 'string' then error('json: expected string') end
  local pos = 1
  local len = #str

  local function fail(msg) error(string.format('json: %s at position %d', msg, pos), 0) end
  local function skip() pos = str:find('[^ \t\r\n]', pos) or (len + 1) end

  local function parseString()
    local buf = {}
    local i = pos + 1
    while true do
      local j = str:find('["\\]', i)
      if not j then fail('unterminated string') end
      if j > i then buf[#buf + 1] = str:sub(i, j - 1) end
      local c = str:sub(j, j)
      if c == '"' then
        pos = j + 1
        return table.concat(buf)
      end
      local e = str:sub(j + 1, j + 1)
      if e == 'u' then
        local cp = tonumber(str:sub(j + 2, j + 5), 16)
        if not cp then fail('bad unicode escape') end
        i = j + 6
        if cp >= 0xD800 and cp <= 0xDBFF and str:sub(i, i + 1) == '\\u' then
          local lo = tonumber(str:sub(i + 2, i + 5), 16)
          if lo and lo >= 0xDC00 and lo <= 0xDFFF then
            cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
            i = i + 6
          end
        end
        buf[#buf + 1] = utf8char(cp)
      else
        local r = simpleEscapes[e]
        if not r then fail('bad escape \\' .. tostring(e)) end
        buf[#buf + 1] = r
        i = j + 2
      end
    end
  end

  local parseValue
  parseValue = function()
    skip()
    local c = str:sub(pos, pos)
    if c == '{' then
      pos = pos + 1
      local obj = json.object({})
      skip()
      if str:sub(pos, pos) == '}' then pos = pos + 1; return obj end
      while true do
        skip()
        if str:sub(pos, pos) ~= '"' then fail('expected string key') end
        local k = parseString()
        skip()
        if str:sub(pos, pos) ~= ':' then fail('expected ":"') end
        pos = pos + 1
        obj[k] = parseValue()
        skip()
        local d = str:sub(pos, pos)
        if d == ',' then pos = pos + 1
        elseif d == '}' then pos = pos + 1; return obj
        else fail('expected "," or "}"') end
      end
    elseif c == '[' then
      pos = pos + 1
      local arr = json.array({})
      skip()
      if str:sub(pos, pos) == ']' then pos = pos + 1; return arr end
      local n = 0
      while true do
        n = n + 1
        arr[n] = parseValue()
        skip()
        local d = str:sub(pos, pos)
        if d == ',' then pos = pos + 1
        elseif d == ']' then pos = pos + 1; return arr
        else fail('expected "," or "]"') end
      end
    elseif c == '"' then
      return parseString()
    elseif str:sub(pos, pos + 3) == 'true' then pos = pos + 4; return true
    elseif str:sub(pos, pos + 4) == 'false' then pos = pos + 5; return false
    elseif str:sub(pos, pos + 3) == 'null' then pos = pos + 4; return nil
    else
      local s, e = str:find('^-?%d+%.?%d*[eE]?[-+]?%d*', pos)
      if not s then fail('unexpected character "' .. c .. '"') end
      local n = tonumber(str:sub(s, e))
      if not n then fail('bad number') end
      pos = e + 1
      return n
    end
  end

  local v = parseValue()
  skip()
  if pos <= len then fail('trailing characters') end
  return v
end

return json
