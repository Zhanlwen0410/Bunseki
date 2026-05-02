import { app, BrowserWindow, Menu, dialog, ipcMain } from 'electron'
import { spawn, type ChildProcess } from 'node:child_process'
import * as fs from 'node:fs/promises'
import * as http from 'node:http'
import * as path from 'node:path'

const isDev = !app.isPackaged
/** dist-electron/ when running from compiled bundle */
const electronDist = __dirname
const desktopRoot = path.join(electronDist, '..')
const repoRoot = path.join(desktopRoot, '..')
const recentFilesPath = path.join(repoRoot, 'data', 'recent_files.json')

let apiBaseUrl = ''
let pythonChild: ChildProcess | null = null
let menuLang: 'zh' | 'ja' | 'en' = 'en'

async function appendLog(line: string): Promise<void> {
  try {
    const logPath = path.join(repoRoot, 'data', 'logs', 'electron-main.log')
    await fs.mkdir(path.dirname(logPath), { recursive: true })
    await fs.appendFile(logPath, `[${new Date().toISOString()}] ${line}\n`, { encoding: 'utf-8' })
  } catch {
    // ignore logging failures
  }
}

process.on('uncaughtException', (err) => {
  const msg = `uncaughtException: ${err?.stack || err?.message || String(err)}`
  console.error(msg)
  void appendLog(msg)
  try {
    dialog.showErrorBox('Bunseki', msg)
  } catch {
    // ignore
  }
})

process.on('unhandledRejection', (reason) => {
  const msg = `unhandledRejection: ${String(reason)}`
  console.error(msg)
  void appendLog(msg)
})

function sendMenuAction(action: string): void {
  const win = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0]
  if (!win) {
    return
  }
  win.webContents.send('bunseki:menu-action', action)
}

function getApiPort(): string {
  return process.env.WMIX_API_PORT || '8765'
}

function pickPythonCommand(): { command: string; argsPrefix: string[] } {
  const raw = process.env.WMIX_PYTHON?.trim() || 'python'
  const parts = raw.match(/(?:[^\s"]+|"[^"]*")+/g) ?? [raw]
  const normalized = parts.map((p) => p.replace(/^"(.*)"$/, '$1'))
  return {
    command: normalized[0] || 'python',
    argsPrefix: normalized.slice(1),
  }
}

function waitForHealth(port: string, timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const req = http.request(
        {
          hostname: '127.0.0.1',
          port: Number(port),
          path: '/health',
          method: 'GET',
          timeout: 2000,
        },
        (res) => {
          res.resume()
          if (res.statusCode === 200) {
            resolve()
            return
          }
          scheduleRetry()
        },
      )
      req.on('error', () => scheduleRetry())
      req.on('timeout', () => {
        req.destroy()
        scheduleRetry()
      })
      req.end()
    }

    const scheduleRetry = () => {
      if (Date.now() > deadline) {
        reject(new Error('Python API did not become healthy in time.'))
        return
      }
      setTimeout(tryOnce, 250)
    }

    tryOnce()
  })
}

async function startPythonApi(): Promise<void> {
  const port = getApiPort()
  const py = pickPythonCommand()
  const args = [
    ...py.argsPrefix,
    '-m',
    'uvicorn',
    'src.api.server:app',
    '--host',
    '127.0.0.1',
    '--port',
    port,
  ]

  pythonChild = spawn(py.command, args, {
    cwd: repoRoot,
    env: {
      ...process.env,
      WMIX_API_PORT: port,
      // Hard-lock offline mode: avoid any accidental network calls at runtime.
      TRANSFORMERS_OFFLINE: process.env.TRANSFORMERS_OFFLINE || '1',
      HF_HUB_OFFLINE: process.env.HF_HUB_OFFLINE || '1',
      HF_HUB_DISABLE_SYMLINKS_WARNING: process.env.HF_HUB_DISABLE_SYMLINKS_WARNING || '1',
      // Reduce native crash risks on some Windows setups (OpenMP/MKL).
      OMP_NUM_THREADS: process.env.OMP_NUM_THREADS || '1',
      MKL_NUM_THREADS: process.env.MKL_NUM_THREADS || '1',
      TOKENIZERS_PARALLELISM: process.env.TOKENIZERS_PARALLELISM || 'false',
    },
    stdio: isDev ? 'inherit' : 'pipe',
    windowsHide: false,
  })

  pythonChild.on('exit', (code, signal) => {
    if (code && code !== 0 && signal !== 'SIGTERM') {
      console.error(`Python API exited with code ${code}`)
    }
    pythonChild = null
  })

  await waitForHealth(port, 120_000)
  apiBaseUrl = `http://127.0.0.1:${port}`
}

function stopPythonApi(): void {
  if (pythonChild && !pythonChild.killed) {
    pythonChild.kill('SIGTERM')
  }
  pythonChild = null
}

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    show: false,
    backgroundColor: '#ffffff',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(electronDist, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  win.once('ready-to-show', () => {
    win.show()
  })

  win.webContents.on('did-finish-load', async () => {
    await appendLog('did-finish-load')
  })
  win.webContents.on('did-fail-load', async (_evt, errorCode, errorDescription, validatedURL) => {
    const msg = `did-fail-load code=${errorCode} desc=${errorDescription} url=${validatedURL}`
    console.error(msg)
    await appendLog(msg)
    dialog.showErrorBox('Bunseki', msg)
  })
  win.webContents.on('render-process-gone', async (_evt, details) => {
    const msg = `render-process-gone reason=${details.reason} exitCode=${details.exitCode}`
    console.error(msg)
    await appendLog(msg)
    dialog.showErrorBox('Bunseki', msg)
  })
  win.webContents.on('unresponsive', async () => {
    const msg = 'renderer unresponsive'
    console.error(msg)
    await appendLog(msg)
  })
  win.webContents.on('console-message', async (_evt, level, message, line, sourceId) => {
    const msg = `renderer console level=${level} ${sourceId}:${line} ${message}`
    await appendLog(msg)
  })

  if (isDev) {
    void win.loadURL('http://127.0.0.1:5173')
    win.webContents.openDevTools({ mode: 'detach' })
  } else {
    const indexHtml = path.join(desktopRoot, 'dist', 'index.html')
    void win.loadFile(indexHtml)
  }
}

function buildAppMenu(): void {
  const tr = (key: string): string => {
    const dict: Record<typeof menuLang, Record<string, string>> = {
      zh: {
        menuFile: '文件',
        menuView: '视图',
        menuTools: '工具',
        menuHelp: '帮助',
        menuOpenText: '打开文本',
        menuOpenProject: '打开项目',
        menuSaveProject: '保存项目',
        menuExportCsv: '导出 CSV',
        menuExportJson: '导出 JSON',
        menuExportBundle: '导出 Bundle',
        menuExit: '退出',
        menuWorkspace: '工作台',
        menuProfile: '语义域剖面',
        menuKwic: 'KWIC',
        menuLexicon: '词典中心',
        menuWordFrequency: '词频分析',
        menuCompare: '对比',
        menuRunAnalyze: '执行分析',
        menuRunKwic: '执行 KWIC',
        menuAbout: '作者详情',
        help: '帮助',
      },
      ja: {
        menuFile: 'ファイル',
        menuView: '表示',
        menuTools: 'ツール',
        menuHelp: 'ヘルプ',
        menuOpenText: 'テキストを開く',
        menuOpenProject: 'プロジェクトを開く',
        menuSaveProject: 'プロジェクト保存',
        menuExportCsv: 'CSV出力',
        menuExportJson: 'JSON出力',
        menuExportBundle: 'Bundle出力',
        menuExit: '終了',
        menuWorkspace: 'ワークスペース',
        menuProfile: '意味領域プロファイル',
        menuKwic: 'KWIC',
        menuLexicon: '辞書',
        menuWordFrequency: '語頻度分析',
        menuCompare: '比較',
        menuRunAnalyze: '分析を実行',
        menuRunKwic: 'KWICを実行',
        menuAbout: '作者情報',
        help: 'ヘルプ',
      },
      en: {
        menuFile: 'File',
        menuView: 'View',
        menuTools: 'Tools',
        menuHelp: 'Help',
        menuOpenText: 'Open Text',
        menuOpenProject: 'Open Project',
        menuSaveProject: 'Save Project',
        menuExportCsv: 'Export CSV',
        menuExportJson: 'Export JSON',
        menuExportBundle: 'Export Bundle',
        menuExit: 'Exit',
        menuWorkspace: 'Workspace',
        menuProfile: 'Semantic Profile',
        menuKwic: 'KWIC',
        menuLexicon: 'Lexicon',
        menuWordFrequency: 'Word Frequency',
        menuCompare: 'Compare',
        menuRunAnalyze: 'Run Analyze',
        menuRunKwic: 'Run KWIC',
        menuAbout: 'About Bunseki',
        help: 'Help',
      },
    }
    return dict[menuLang][key] || key
  }

  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: tr('menuFile'),
      submenu: [
        { label: tr('menuOpenText'), accelerator: 'CmdOrCtrl+O', click: () => sendMenuAction('file.openText') },
        {
          label: tr('menuOpenProject'),
          accelerator: 'CmdOrCtrl+Shift+O',
          click: () => sendMenuAction('file.openProject'),
        },
        { label: tr('menuSaveProject'), accelerator: 'CmdOrCtrl+S', click: () => sendMenuAction('file.saveProject') },
        { type: 'separator' },
        { label: tr('menuExportCsv'), accelerator: 'CmdOrCtrl+Shift+C', click: () => sendMenuAction('file.exportCsv') },
        { label: tr('menuExportJson'), accelerator: 'CmdOrCtrl+Shift+J', click: () => sendMenuAction('file.exportJson') },
        {
          label: tr('menuExportBundle'),
          accelerator: 'CmdOrCtrl+Shift+B',
          click: () => sendMenuAction('file.exportBundle'),
        },
        { type: 'separator' },
        { role: 'quit', label: tr('menuExit') },
      ],
    },
    {
      label: tr('menuView'),
      submenu: [
        { label: tr('menuWorkspace'), accelerator: 'CmdOrCtrl+1', click: () => sendMenuAction('view.workspace') },
        { label: tr('menuProfile'), accelerator: 'CmdOrCtrl+2', click: () => sendMenuAction('view.profile') },
        { label: tr('menuKwic'), accelerator: 'CmdOrCtrl+3', click: () => sendMenuAction('view.kwic') },
        { label: tr('menuLexicon'), accelerator: 'CmdOrCtrl+4', click: () => sendMenuAction('view.lexicon') },
        { label: tr('menuWordFrequency'), accelerator: 'CmdOrCtrl+5', click: () => sendMenuAction('view.wordFrequency') },
        { label: tr('menuCompare'), accelerator: 'CmdOrCtrl+6', click: () => sendMenuAction('view.compare') },
        { type: 'separator' },
        { role: 'reload' },
        { role: 'resetzoom' },
        { role: 'zoomin' },
        { role: 'zoomout' },
      ],
    },
    {
      label: tr('menuTools'),
      submenu: [
        { label: tr('menuRunAnalyze'), accelerator: 'F5', click: () => sendMenuAction('tools.analyze') },
        { label: tr('menuRunKwic'), accelerator: 'F6', click: () => sendMenuAction('tools.kwic') },
      ],
    },
    {
      label: tr('menuHelp'),
      submenu: [
        { label: tr('menuAbout'), click: () => sendMenuAction('help.about') },
        { label: tr('help'), accelerator: 'F1', click: () => sendMenuAction('help.help') },
      ],
    },
  ]
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

ipcMain.handle('wmatrix:get-api-base', () => apiBaseUrl)

ipcMain.handle('bunseki:open-text-file', async () => {
  const win = BrowserWindow.getFocusedWindow()
  if (!win) {
    return { canceled: true }
  }
  const res = await dialog.showOpenDialog(win, {
    properties: ['openFile'],
    filters: [{ name: 'Text', extensions: ['txt', 'md', 'csv', 'json'] }, { name: 'All', extensions: ['*'] }],
  })
  if (res.canceled || !res.filePaths[0]) {
    return { canceled: true }
  }
  const filePath = res.filePaths[0]
  const content = await fs.readFile(filePath, { encoding: 'utf-8' })
  return { canceled: false, path: filePath, content }
})

ipcMain.handle('bunseki:open-project-file', async () => {
  const win = BrowserWindow.getFocusedWindow()
  if (!win) {
    return { canceled: true }
  }
  const res = await dialog.showOpenDialog(win, {
    properties: ['openFile'],
    filters: [{ name: 'Bunseki Project', extensions: ['wmja.json', 'json'] }, { name: 'All', extensions: ['*'] }],
  })
  if (res.canceled || !res.filePaths[0]) {
    return { canceled: true }
  }
  const filePath = res.filePaths[0]
  const content = await fs.readFile(filePath, { encoding: 'utf-8' })
  return { canceled: false, path: filePath, content }
})

ipcMain.handle('bunseki:open-text-path', async (_evt, args: { path?: string }) => {
  const filePath = String(args?.path || '').trim()
  if (!filePath) {
    return { canceled: true }
  }
  try {
    const content = await fs.readFile(filePath, { encoding: 'utf-8' })
    return { canceled: false, path: filePath, content }
  } catch (e) {
    return { canceled: true, error: e instanceof Error ? e.message : String(e) }
  }
})

ipcMain.handle('bunseki:open-project-path', async (_evt, args: { path?: string }) => {
  const filePath = String(args?.path || '').trim()
  if (!filePath) {
    return { canceled: true }
  }
  try {
    const content = await fs.readFile(filePath, { encoding: 'utf-8' })
    return { canceled: false, path: filePath, content }
  } catch (e) {
    return { canceled: true, error: e instanceof Error ? e.message : String(e) }
  }
})

ipcMain.handle('bunseki:path-exists', async (_evt, args: { path?: string }) => {
  const filePath = String(args?.path || '').trim()
  if (!filePath) {
    return { exists: false }
  }
  try {
    await fs.access(filePath)
    return { exists: true }
  } catch {
    return { exists: false }
  }
})

ipcMain.handle('bunseki:save-file', async (_evt, args: { suggestedName: string; content: string }) => {
  const win = BrowserWindow.getFocusedWindow()
  if (!win) {
    return { canceled: true }
  }
  const res = await dialog.showSaveDialog(win, {
    defaultPath: args.suggestedName,
    filters: [{ name: 'All', extensions: ['*'] }],
  })
  if (res.canceled || !res.filePath) {
    return { canceled: true }
  }
  await fs.writeFile(res.filePath, args.content, { encoding: 'utf-8' })
  return { canceled: false, path: res.filePath }
})

ipcMain.handle('bunseki:get-recent-files', async () => {
  try {
    const raw = await fs.readFile(recentFilesPath, { encoding: 'utf-8' })
    return JSON.parse(raw)
  } catch {
    return {
      recent_text_files: [],
      recent_lexicon_files: [],
      recent_project_files: [],
    }
  }
})

ipcMain.handle('bunseki:set-recent-files', async (_evt, payload: Record<string, unknown>) => {
  await fs.mkdir(path.dirname(recentFilesPath), { recursive: true })
  await fs.writeFile(recentFilesPath, JSON.stringify(payload, null, 2), { encoding: 'utf-8' })
  return { ok: true }
})

ipcMain.handle('bunseki:set-menu-language', async (_evt, args: { lang?: string }) => {
  const next = String(args?.lang || '').toLowerCase()
  if (next === 'zh' || next === 'ja' || next === 'en') {
    menuLang = next
    buildAppMenu()
  }
  return { ok: true }
})

// Settings (whitelisted) - semantic constraints JSON.
const constraintsPath = path.join(repoRoot, 'data', 'mapping', 'semantic_constraints.json')
ipcMain.handle('bunseki:get-constraints', async () => {
  try {
    const raw = await fs.readFile(constraintsPath, { encoding: 'utf-8' })
    return { ok: true, data: JSON.parse(raw) as unknown }
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) }
  }
})

ipcMain.handle('bunseki:set-constraints', async (_evt, args: { content?: unknown }) => {
  try {
    await fs.mkdir(path.dirname(constraintsPath), { recursive: true })
    const payload = JSON.stringify(args?.content ?? {}, null, 2)
    await fs.writeFile(constraintsPath, payload, { encoding: 'utf-8' })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) }
  }
})

app.whenReady().then(async () => {
  try {
    await startPythonApi()
  } catch (e) {
    console.error(e)
    stopPythonApi()
    const msg =
      e instanceof Error
        ? e.message
        : 'Failed to start Python API. Install deps: pip install -r requirements.txt'
    dialog.showErrorBox('Bunseki', msg)
    app.quit()
    return
  }

  createWindow()
  buildAppMenu()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopPythonApi()
    app.quit()
  }
})

app.on('before-quit', () => {
  stopPythonApi()
})
