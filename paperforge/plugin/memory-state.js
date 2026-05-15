const fs = require('fs');
const path = require('path');
const { execFileSync } = require('node:child_process');

function resolveVaultPaths(vaultPath) {
  const systemDir = path.join(vaultPath, 'System', 'PaperForge');
  return {
    vault: vaultPath,
    systemDir,
    indexesDir: path.join(systemDir, 'indexes'),
    logsDir: path.join(systemDir, 'logs'),
    dbPath: path.join(systemDir, 'indexes', 'paperforge.db'),
    memoryStatePath: path.join(systemDir, 'indexes', 'memory-runtime-state.json'),
    vectorStatePath: path.join(systemDir, 'indexes', 'vector-runtime-state.json'),
    healthStatePath: path.join(systemDir, 'indexes', 'runtime-health.json'),
    buildStatePath: path.join(systemDir, 'indexes', 'vector-build-state.json'),
    pluginDataPath: path.join(vaultPath, '.obsidian', 'plugins', 'paperforge', 'data.json'),
    pfJsonPath: path.join(vaultPath, 'paperforge.json'),
  };
}

function readJSONFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch (_) { return null; }
}

function getMemoryRuntime(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.memoryStatePath);
}

function getVectorRuntime(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.vectorStatePath);
}

function getRuntimeHealth(vaultPath) {
  const paths = resolveVaultPaths(vaultPath);
  return readJSONFile(paths.healthStatePath);
}

function isMemoryReady(vaultPath) {
  const s = getMemoryRuntime(vaultPath);
  return !!(s && s.paper_count_db > 0 && !s.needs_rebuild);
}

function isVectorReady(vaultPath) {
  const s = getVectorRuntime(vaultPath);
  if (!s) return false;
  if (!s.enabled) return false;
  if (!s.deps_installed) return false;
  if (!s.db_exists) return false;
  if (s.chunk_count === 0) return false;
  return true;
}

function isHealthOk(vaultPath) {
  const s = getRuntimeHealth(vaultPath);
  return !!(s && s.summary && s.summary.status === 'ok');
}

function getMemoryStatusText(vaultPath) {
  const s = getMemoryRuntime(vaultPath);
  if (!s || s.paper_count_db === 0) return 'DB not found. Run paperforge memory build.';
  return 'Papers: ' + s.paper_count_db + ' | ' + (s.fresh ? 'fresh' : 'stale');
}

function getVectorStatusText(vaultPath) {
  const s = getVectorRuntime(vaultPath);
  if (!s) return 'Status unavailable';
  return 'Chunks: ' + s.chunk_count + ' | ' + s.model + ' | ' + s.mode;
}

function resolvePythonPath(vaultPath, settings) {
  if (settings && settings.python_path && settings.python_path.trim()) {
    var p = settings.python_path.trim();
    if (fs.existsSync(p)) return { path: p, source: 'manual', extraArgs: [] };
  }
  var venvCandidates = [
    path.join(vaultPath, '.paperforge-test-venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, '.venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, 'venv', 'Scripts', 'python.exe'),
  ];
  for (var i = 0; i < venvCandidates.length; i++) {
    if (fs.existsSync(venvCandidates[i])) return { path: venvCandidates[i], source: 'auto-detected', extraArgs: [] };
  }
  var systemCandidates = [{path:'python',extraArgs:[]},{path:'python3',extraArgs:[]}];
  for (var j = 0; j < systemCandidates.length; j++) {
    try {
      var c = systemCandidates[j];
      var out = execFileSync(c.path, c.extraArgs.concat(['--version']), {encoding:'utf-8',timeout:5000,windowsHide:true});
      if (out && out.toLowerCase().indexOf('python') !== -1) return { path:c.path, source:'auto-detected', extraArgs:c.extraArgs };
    } catch (_) {}
  }
  return { path: 'python', source: 'auto-detected', extraArgs: [] };
}

var _cachedPython = null;
function getCachedPython(vaultPath, settings) {
  if (!_cachedPython) _cachedPython = resolvePythonPath(vaultPath, settings);
  return _cachedPython;
}

function buildSnapshot(vaultPath, _readFn, _resolvePaths) {
  var readFn = _readFn || readJSONFile;
  var resolvePaths = _resolvePaths || resolveVaultPaths;
  var paths = resolvePaths(vaultPath);

  var memory = readFn(paths.memoryStatePath);
  var vector = readFn(paths.vectorStatePath);
  var health = readFn(paths.healthStatePath);

  var memoryOk = !!(memory && memory.paper_count_db > 0 && !memory.needs_rebuild);
  var vectorOk = !!(vector && vector.enabled && vector.deps_installed && vector.db_exists && vector.chunk_count > 0);

  return {
    memory: memory,
    vector: vector,
    health: health,
    updatedAt: (memory && memory.updated_at) || (vector && vector.updated_at) || '',
    summary: {
      status: memoryOk && vectorOk ? 'ready' : 'degraded',
      memoryReady: memoryOk,
      vectorReady: vectorOk,
      healthOk: !!(health && health.summary && health.summary.status === 'ok'),
    },
  };
}

module.exports = {
  resolveVaultPaths: resolveVaultPaths,
  readJSONFile: readJSONFile,
  getMemoryRuntime: getMemoryRuntime,
  getVectorRuntime: getVectorRuntime,
  getRuntimeHealth: getRuntimeHealth,
  isMemoryReady: isMemoryReady,
  isVectorReady: isVectorReady,
  isHealthOk: isHealthOk,
  getMemoryStatusText: getMemoryStatusText,
  getVectorStatusText: getVectorStatusText,
  resolvePythonPath: resolvePythonPath,
  getCachedPython: getCachedPython,
  buildSnapshot: buildSnapshot,
};
