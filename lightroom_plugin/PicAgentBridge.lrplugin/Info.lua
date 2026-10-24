return {
  LrSdkVersion = 10.0,
  LrSdkMinimumVersion = 6.0,
  LrToolkitIdentifier = 'com.bbshark.picagent.bridge',
  LrPluginName = 'Pic Agent Bridge',
  LrForceInitPlugin = true,
  LrInitPlugin = 'Init.lua',
  LrEnablePlugin = 'Init.lua',
  LrShutdownPlugin = 'Shutdown.lua',
  LrDisablePlugin = 'Shutdown.lua',
  LrLibraryMenuItems = {
    { title = 'Pic Agent Bridge: 状态', file = 'MenuStatus.lua' },
    { title = 'Pic Agent Bridge: 重启服务', file = 'MenuRestart.lua' },
  },
  VERSION = { major = 0, minor = 1, revision = 0, build = 1 },
}
