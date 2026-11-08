return {
  LrSdkVersion = 10.0,
  LrSdkMinimumVersion = 6.0,
  LrToolkitIdentifier = 'com.runnerback.lightroomagent',
  LrPluginName = 'Lightroom Agent',
  LrForceInitPlugin = true,
  LrInitPlugin = 'Init.lua',
  LrEnablePlugin = 'Init.lua',
  LrShutdownPlugin = 'Shutdown.lua',
  LrDisablePlugin = 'Shutdown.lua',
  LrLibraryMenuItems = {
    { title = 'Lightroom Agent: Status', file = 'MenuStatus.lua' },
    { title = 'Lightroom Agent: Restart service', file = 'MenuRestart.lua' },
  },
  VERSION = { major = 0, minor = 3, revision = 0, build = 0 },
}
