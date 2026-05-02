import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('wmatrixDesktop', {
  getApiBase: (): Promise<string> => ipcRenderer.invoke('wmatrix:get-api-base'),
  openTextFile: (): Promise<{ canceled: boolean; path?: string; content?: string }> =>
    ipcRenderer.invoke('bunseki:open-text-file'),
  openProjectFile: (): Promise<{ canceled: boolean; path?: string; content?: string }> =>
    ipcRenderer.invoke('bunseki:open-project-file'),
  openTextPath: (filePath: string): Promise<{ canceled: boolean; path?: string; content?: string; error?: string }> =>
    ipcRenderer.invoke('bunseki:open-text-path', { path: filePath }),
  openProjectPath: (filePath: string): Promise<{ canceled: boolean; path?: string; content?: string; error?: string }> =>
    ipcRenderer.invoke('bunseki:open-project-path', { path: filePath }),
  pathExists: (filePath: string): Promise<{ exists: boolean }> => ipcRenderer.invoke('bunseki:path-exists', { path: filePath }),
  saveFile: (suggestedName: string, content: string): Promise<{ canceled: boolean; path?: string }> =>
    ipcRenderer.invoke('bunseki:save-file', { suggestedName, content }),
  getRecentFiles: (): Promise<Record<string, unknown>> => ipcRenderer.invoke('bunseki:get-recent-files'),
  setRecentFiles: (payload: Record<string, unknown>): Promise<{ ok: boolean }> =>
    ipcRenderer.invoke('bunseki:set-recent-files', payload),
  onMenuAction: (handler: (action: string) => void): (() => void) => {
    const listener = (_event: unknown, action: string) => handler(action)
    ipcRenderer.on('bunseki:menu-action', listener)
    return () => ipcRenderer.removeListener('bunseki:menu-action', listener)
  },
  setMenuLanguage: (lang: string): Promise<{ ok: boolean }> => ipcRenderer.invoke('bunseki:set-menu-language', { lang }),
  getConstraints: (): Promise<{ ok: boolean; data?: unknown; error?: string }> => ipcRenderer.invoke('bunseki:get-constraints'),
  setConstraints: (content: unknown): Promise<{ ok: boolean; error?: string }> =>
    ipcRenderer.invoke('bunseki:set-constraints', { content }),
})
