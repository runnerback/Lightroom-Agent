-- Handlers.lua : command implementations. Each handler is function(params, server) -> result table.
local LrApplication = import 'LrApplication'
local LrExportSession = import 'LrExportSession'
local LrFileUtils = import 'LrFileUtils'
local LrPathUtils = import 'LrPathUtils'
local LrDate = import 'LrDate'

local json = require 'json'

local H = {}
local cache = {} -- path | 'name:<file>' | 'uuid:<uuid>'  ->  LrPhoto

local function catalog() return LrApplication.activeCatalog() end
local function leaf(path) return LrPathUtils.leafName(path) end

local function remember(ph, path, uuid)
  if path then
    cache[path] = ph
    cache['name:' .. leaf(path)] = ph
  end
  if uuid then cache['uuid:' .. uuid] = ph end
end

local function resolvePhoto(cat, item)
  if type(item) == 'string' then item = { path = item } end
  if type(item) ~= 'table' then return nil end
  local ph
  if item.path then
    ph = cache[item.path]
    if not ph then
      local ok, r = pcall(cat.findPhotoByPath, cat, item.path)
      if ok then ph = r end
    end
    if not ph then ph = cache['name:' .. leaf(item.path)] end
  end
  if not ph and item.uuid then
    ph = cache['uuid:' .. item.uuid]
    if not ph then
      local ok, r = pcall(cat.getPhotoByUuid, cat, item.uuid)
      if ok then ph = r end
    end
  end
  if not ph and item.name then ph = cache['name:' .. item.name] end
  if ph then remember(ph, item.path, item.uuid) end
  return ph
end

local function resolveMany(cat, list)
  local photos, missing = {}, json.array({})
  for _, it in ipairs(list or {}) do
    local ph = resolvePhoto(cat, it)
    if ph then
      photos[#photos + 1] = ph
    else
      missing[#missing + 1] = type(it) == 'table' and (it.path or it.name or it.uuid) or tostring(it)
    end
  end
  return photos, missing
end

local function findFolder(cat, path)
  local ok, f = pcall(cat.getFolderByPath, cat, path)
  if ok and f then return f end
  local norm = (path:gsub('/+$', ''))
  local function walk(folder)
    local fp = ((folder:getPath() or ''):gsub('/+$', ''))
    if fp == norm then return folder end
    for _, c in ipairs(folder:getChildren() or {}) do
      local r = walk(c)
      if r then return r end
    end
    return nil
  end
  for _, root in ipairs(cat:getFolders() or {}) do
    local r = walk(root)
    if r then return r end
  end
  return nil
end

local function findCollection(cat, name)
  local function walk(container)
    for _, c in ipairs(container:getChildCollections() or {}) do
      if c:getName() == name then return c end
    end
    for _, s in ipairs(container:getChildCollectionSets() or {}) do
      local r = walk(s)
      if r then return r end
    end
    return nil
  end
  return walk(cat)
end

local RAW_KEYS = { 'path', 'rating', 'pickStatus', 'colorNameForLabel', 'width', 'height', 'uuid', 'fileSize', 'isVirtualCopy' }
local FMT_KEYS = { 'dateTimeOriginal', 'isoSpeedRating', 'aperture', 'shutterSpeed', 'focalLength', 'lens', 'cameraModel', 'keywordTags', 'copyName' }

-- Returns two accessor functions raw(ph,key), fmt(ph,key) backed by batch reads with per-photo fallback.
local function batchMeta(cat, photos)
  local okR, raw = pcall(cat.batchGetRawMetadata, cat, photos, RAW_KEYS)
  local okF, fmt = pcall(cat.batchGetFormattedMetadata, cat, photos, FMT_KEYS)
  if not okR or type(raw) ~= 'table' then raw = {} end
  if not okF or type(fmt) ~= 'table' then fmt = {} end
  local function get(ph, tbl, key, formatted)
    local t = tbl[ph]
    if t and t[key] ~= nil then return t[key] end
    local ok, v = pcall(formatted and ph.getFormattedMetadata or ph.getRawMetadata, ph, key)
    if ok then return v end
    return nil
  end
  return function(ph, key) return get(ph, raw, key, false) end,
         function(ph, key) return get(ph, fmt, key, true) end
end

local function describe(photos, cat)
  local raw, fmt = batchMeta(cat, photos)
  local out = json.array({})
  for _, ph in ipairs(photos) do
    local path = raw(ph, 'path')
    local uuid = raw(ph, 'uuid')
    remember(ph, path, uuid)
    out[#out + 1] = {
      path = path, name = path and leaf(path) or nil, uuid = uuid,
      rating = raw(ph, 'rating') or 0, pick = raw(ph, 'pickStatus') or 0, label = raw(ph, 'colorNameForLabel'),
      width = raw(ph, 'width'), height = raw(ph, 'height'), size = raw(ph, 'fileSize'), virtual = raw(ph, 'isVirtualCopy'),
      datetime = fmt(ph, 'dateTimeOriginal'), iso = fmt(ph, 'isoSpeedRating'), aperture = fmt(ph, 'aperture'),
      shutter = fmt(ph, 'shutterSpeed'), focal = fmt(ph, 'focalLength'), lens = fmt(ph, 'lens'),
      camera = fmt(ph, 'cameraModel'), keywords = fmt(ph, 'keywordTags'), copy = fmt(ph, 'copyName'),
    }
  end
  return out
end

local function withWrite(cat, name, fn, timeout)
  local r = cat:withWriteAccessDo(name, fn, { timeout = timeout or 60 })
  if r == 'aborted' then
    error('catalog write aborted (timeout ' .. tostring(timeout or 60) .. 's). Is a dialog open in Lightroom?')
  end
  return r
end

local function normLabel(l)
  if l == nil then return nil end
  if l == '' or l == 'none' or l == 'grey' or l == 'gray' then return 'none' end
  return l
end

local function filterPhotos(cat, photos, flt)
  if not flt then return photos end
  local raw = batchMeta(cat, photos)
  local out = {}
  for _, ph in ipairs(photos) do
    local keep = true
    local rating = raw(ph, 'rating') or 0
    if flt.min_rating and rating < flt.min_rating then keep = false end
    if flt.max_rating and rating > flt.max_rating then keep = false end
    if flt.pick ~= nil and (raw(ph, 'pickStatus') or 0) ~= flt.pick then keep = false end
    if flt.label and normLabel(raw(ph, 'colorNameForLabel')) ~= normLabel(flt.label) then keep = false end
    if keep then out[#out + 1] = ph end
  end
  return out
end

local function gatherPhotos(cat, p)
  local photos, missing = {}, json.array({})
  if p.items or p.paths then
    photos, missing = resolveMany(cat, p.items or p.paths)
  elseif p.collection then
    local col = findCollection(cat, p.collection)
    if not col then error('collection not found: ' .. tostring(p.collection)) end
    photos = col:getPhotos()
  elseif p.folder then
    local folder = findFolder(cat, p.folder)
    if not folder then error('folder not in catalog: ' .. tostring(p.folder)) end
    photos = folder:getPhotos(p.include_children == true)
  elseif p.selection then
    photos = cat:getTargetPhotos()
  else
    error('give items/paths, collection, folder or selection')
  end
  return filterPhotos(cat, photos, p.filter), missing
end

---------------------------------------------------------------- read commands

function H.ping(_, server)
  local cat = catalog()
  return {
    pong = true,
    plugin = 'Pic Agent Bridge',
    version = server and server.VERSION or '?',
    lightroom = LrApplication.versionString(),
    catalog = cat:getPath(),
    stats = server and server.stats or nil,
  }
end

function H.list_folder(p)
  local cat = catalog()
  if not p.path then error('path required') end
  local folder = findFolder(cat, p.path)
  if not folder then error('folder not in catalog: ' .. p.path) end
  local photos = folder:getPhotos(p.include_children == true)
  return { folder = p.path, count = #photos, photos = describe(photos, cat) }
end

function H.list_collection(p)
  local cat = catalog()
  local col = findCollection(cat, p.name)
  if not col then error('collection not found: ' .. tostring(p.name)) end
  local photos = col:getPhotos()
  return { collection = p.name, count = #photos, photos = describe(photos, cat) }
end

function H.get_selection()
  local cat = catalog()
  local photos = cat:getTargetPhotos()
  return { count = #photos, photos = describe(photos, cat) }
end

function H.get_develop(p)
  local cat = catalog()
  local ph = resolvePhoto(cat, p)
  if not ph then error('photo not found: ' .. tostring(p.path)) end
  return { path = p.path, settings = ph:getDevelopSettings() }
end

function H.catalog_info(p)
  local cat = catalog()
  local folders = json.array({})
  local function walk(folder, depth)
    local n = nil
    if p.count then
      local ok, c = pcall(function() return #folder:getPhotos(false) end)
      if ok then n = c end
    end
    folders[#folders + 1] = { path = folder:getPath(), photos = n, depth = depth }
    for _, c in ipairs(folder:getChildren() or {}) do walk(c, depth + 1) end
  end
  for _, root in ipairs(cat:getFolders() or {}) do walk(root, 0) end
  return { catalog = cat:getPath(), folders = folders }
end

---------------------------------------------------------------- UI commands

function H.select(p)
  local cat = catalog()
  local photos, missing = resolveMany(cat, p.items or p.paths)
  if #photos > 0 then cat:setSelectedPhotos(photos[1], photos) end
  return { selected = #photos, missing = missing }
end

function H.show_folder(p)
  local cat = catalog()
  local folder = findFolder(cat, p.path)
  if not folder then error('folder not in catalog: ' .. tostring(p.path)) end
  cat:setActiveSources({ folder })
  return { shown = p.path }
end

function H.show_collection(p)
  local cat = catalog()
  local col = findCollection(cat, p.name)
  if not col then error('collection not found: ' .. tostring(p.name)) end
  cat:setActiveSources({ col })
  return { shown = p.name }
end

---------------------------------------------------------------- write commands

function H.set_meta(p)
  local cat = catalog()
  local items = p.items or {}
  local updated, missing, errors = 0, json.array({}), json.array({})
  withWrite(cat, p.history or 'Pic Agent: 元数据', function()
    for _, it in ipairs(items) do
      local ph = resolvePhoto(cat, it)
      if not ph then
        missing[#missing + 1] = it.path or it.name or it.uuid
      else
        local ok, e = pcall(function()
          if it.rating ~= nil then
            local r = tonumber(it.rating) or 0
            ph:setRawMetadata('rating', r > 0 and r or nil)
          end
          if it.pick ~= nil then ph:setRawMetadata('pickStatus', tonumber(it.pick) or 0) end
          if it.label ~= nil then ph:setRawMetadata('colorNameForLabel', normLabel(it.label)) end
          if it.title ~= nil then ph:setRawMetadata('title', it.title) end
          if it.caption ~= nil then ph:setRawMetadata('caption', it.caption) end
        end)
        if ok then updated = updated + 1 else errors[#errors + 1] = { path = it.path, error = tostring(e) } end
      end
    end
  end, p.timeout or 120)
  return { updated = updated, missing = missing, errors = errors }
end

function H.add_keywords(p)
  local cat = catalog()
  local names = {}
  for _, it in ipairs(p.items or {}) do
    for _, k in ipairs(it.keywords or {}) do names[k] = true end
  end
  local kws = {}
  withWrite(cat, 'Pic Agent: 创建关键字', function()
    for name in pairs(names) do kws[name] = cat:createKeyword(name, {}, true, nil, true) end
  end, 60)
  local added, missing = 0, json.array({})
  withWrite(cat, 'Pic Agent: 关键字', function()
    for _, it in ipairs(p.items or {}) do
      local ph = resolvePhoto(cat, it)
      if ph then
        for _, k in ipairs(it.keywords or {}) do
          if kws[k] then
            ph:addKeyword(kws[k])
            added = added + 1
          end
        end
      else
        missing[#missing + 1] = it.path or it.name
      end
    end
  end, p.timeout or 120)
  return { added = added, missing = missing }
end

function H.collection_add(p)
  local cat = catalog()
  if not p.name then error('name required') end
  local photos, missing = resolveMany(cat, p.items or p.paths)
  local set, col = nil, nil
  if p.set and p.set ~= '' then
    withWrite(cat, 'Pic Agent: 收藏集组', function()
      set = cat:createCollectionSet(p.set, nil, true)
    end, 60)
  end
  withWrite(cat, 'Pic Agent: 创建收藏集', function()
    col = cat:createCollection(p.name, set, true)
  end, 60)
  if not col then error('could not create collection ' .. p.name) end
  withWrite(cat, 'Pic Agent: 收藏集照片', function()
    if p.replace then col:removeAllPhotos() end
    if #photos > 0 then col:addPhotos(photos) end
  end, p.timeout or 120)
  if p.show then cat:setActiveSources({ col }) end
  return { collection = p.name, set = p.set, added = #photos, missing = missing }
end

local presetCounter = 0
local function applySettings(ph, settings, historyName)
  local ok = pcall(ph.applyDevelopSettings, ph, settings, historyName)
  if ok then return true end
  presetCounter = presetCounter + 1
  local preset = LrApplication.addDevelopPresetForPlugin(_PLUGIN, 'PicAgent-' .. presetCounter, settings)
  ph:applyDevelopPreset(preset, _PLUGIN)
  return true
end

function H.apply_develop(p)
  local cat = catalog()
  local global = p.settings or {}
  local items = p.items
  if not items then
    items = {}
    for _, path in ipairs(p.paths or {}) do items[#items + 1] = { path = path } end
  end
  local updated, missing, errors = 0, json.array({}), json.array({})
  withWrite(cat, p.history or 'Pic Agent: 修图参数', function()
    for _, it in ipairs(items) do
      local ph = resolvePhoto(cat, it)
      if not ph then
        missing[#missing + 1] = it.path or it.name
      else
        local s = {}
        for k, v in pairs(global) do s[k] = v end
        for k, v in pairs(it.settings or {}) do s[k] = v end
        local ok, e = pcall(applySettings, ph, s, p.history or 'Pic Agent')
        if ok then updated = updated + 1 else errors[#errors + 1] = { path = it.path, error = tostring(e) } end
      end
    end
  end, p.timeout or 300)
  return { updated = updated, missing = missing, errors = errors }
end

function H.export(p)
  local cat = catalog()
  if not p.dest then error('dest required') end
  local photos, missing = gatherPhotos(cat, p)
  if #photos == 0 then error('no photos matched') end
  LrFileUtils.createAllDirectories(p.dest)

  local fmt = p.format or 'JPEG'
  local longEdge = tonumber(p.long_edge)
  local settings = {
    LR_exportServiceProvider = 'com.adobe.ag.export.file',
    LR_export_destinationType = 'specificFolder',
    LR_export_destinationPathPrefix = p.dest,
    LR_export_useSubfolder = false,
    LR_collisionHandling = p.collision or 'overwrite',
    LR_format = fmt,
    LR_jpeg_quality = (tonumber(p.quality) or 90) / 100,
    LR_jpeg_useLimitSize = false,
    LR_export_colorSpace = p.color_space or 'sRGB',
    LR_export_bitDepth = tonumber(p.bit_depth) or (fmt == 'TIFF' and 16 or 8),
    LR_size_doConstrain = longEdge ~= nil,
    LR_size_resizeType = 'longEdge',
    LR_size_maxHeight = longEdge or 0,
    LR_size_maxWidth = longEdge or 0,
    LR_size_units = 'pixels',
    LR_size_doNotEnlarge = true,
    LR_size_resolution = 300,
    LR_size_resolutionUnits = 'inch',
    LR_outputSharpeningOn = p.sharpen ~= false,
    LR_outputSharpeningMedia = p.sharpen_media or 'screen',
    LR_outputSharpeningLevel = tonumber(p.sharpen_level) or 2,
    LR_minimizeEmbeddedMetadata = false,
    LR_embeddedMetadataOption = p.metadata or 'all',
    LR_metadata_keywordOptions = 'lightroomHierarchical',
    LR_removeLocationMetadata = p.keep_location ~= true,
    LR_renamingTokensOn = p.tokens ~= nil,
    LR_tokens = p.tokens or '{{image_name}}',
    LR_tokenCustomString = p.custom_text or '',
    LR_initialSequenceNumber = 1,
    LR_reimportExportedPhoto = false,
    LR_useWatermark = false,
    LR_includeVideoFiles = false,
    LR_export_postProcessing = 'doNothing',
  }
  if fmt == 'TIFF' then settings.LR_tiff_compressionMethod = 'compressionMethod_ZIP' end
  if fmt == 'DNG' or fmt == 'ORIGINAL' then settings.LR_size_doConstrain = false end
  for k, v in pairs(p.raw_settings or {}) do settings[k] = v end

  local t0 = LrDate.currentTime()
  local session = LrExportSession { photosToExport = photos, exportSettings = settings }
  session:doExportOnCurrentTask()

  local files = json.array({})
  for f in LrFileUtils.files(p.dest) do
    local a = LrFileUtils.fileAttributes(f)
    if a and a.fileModificationDate and a.fileModificationDate >= t0 - 2 then files[#files + 1] = f end
  end
  table.sort(files)
  return {
    requested = #photos, written = #files, dest = p.dest, files = files,
    missing = missing, seconds = LrDate.currentTime() - t0,
  }
end

return H
