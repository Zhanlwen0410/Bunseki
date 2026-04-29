export {}

declare global {
  interface Window {
    /** Present when running inside Electron preload. */
    wmatrixDesktop?: {
      getApiBase: () => Promise<string>
      openTextFile: () => Promise<{ canceled: boolean; path?: string; content?: string }>
      openProjectFile: () => Promise<{ canceled: boolean; path?: string; content?: string }>
      openTextPath: (filePath: string) => Promise<{ canceled: boolean; path?: string; content?: string; error?: string }>
      openProjectPath: (filePath: string) => Promise<{ canceled: boolean; path?: string; content?: string; error?: string }>
      pathExists: (filePath: string) => Promise<{ exists: boolean }>
      saveFile: (suggestedName: string, content: string) => Promise<{ canceled: boolean; path?: string }>
      getRecentFiles: () => Promise<Record<string, unknown>>
      setRecentFiles: (payload: Record<string, unknown>) => Promise<{ ok: boolean }>
      onMenuAction: (handler: (action: string) => void) => () => void
      setMenuLanguage: (lang: string) => Promise<{ ok: boolean }>
    }
  }
}
