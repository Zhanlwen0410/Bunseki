import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { apiGetJson, apiPostJson } from '../api/client'
import type { AnalyzeResponse, AnalysisResult, ProfileRow } from '../types/models'

export type BootstrapPayload = {
  sample_text: string
  lexicon_path: string
  categories: Record<string, Record<string, string>>
  help: string
  about?: {
    license?: string
    organization?: string
    author?: string
    cc_icon_url?: string
  }
}

type WorkbenchContextValue = {
  apiBase: string
  bootstrap: BootstrapPayload | null
  reloadBootstrap: () => Promise<void>
  text: string
  setText: (v: string) => void
  language: string
  setLanguage: (v: string) => void
  mode: string
  setMode: (v: string) => void
  tokenizer: string
  setTokenizer: (v: string) => void
  minFrequency: number
  setMinFrequency: (v: number) => void
  topN: string
  setTopN: (v: string) => void
  lexiconPath: string
  setLexiconPath: (v: string) => void
  analyzing: boolean
  analyzeError: string | null
  result: AnalysisResult | null
  profile: ProfileRow[]
  selectedDomain: string
  setSelectedDomain: (v: string) => void
  keyword: string
  setKeyword: (v: string) => void
  compareLeft: string
  setCompareLeft: (v: string) => void
  compareRight: string
  setCompareRight: (v: string) => void
  runAnalyze: () => Promise<void>
  setResultState: (v: AnalysisResult | null, profileRows?: ProfileRow[]) => void
}

const WorkbenchContext = createContext<WorkbenchContextValue | null>(null)

export function WorkbenchProvider({
  apiBase,
  children,
}: {
  apiBase: string
  children: ReactNode
}): JSX.Element {
  const [bootstrap, setBootstrap] = useState<BootstrapPayload | null>(null)
  const [text, setText] = useState('')
  const [language, setLanguage] = useState('ja')
  const [tokenizer, setTokenizer] = useState('sudachi')
  const [mode, setMode] = useState('C')
  const [minFrequency, setMinFrequency] = useState(1)
  const [topN, setTopN] = useState('')
  const [lexiconPath, setLexiconPath] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [profile, setProfile] = useState<ProfileRow[]>([])
  const [selectedDomain, setSelectedDomain] = useState('')
  const [keyword, setKeyword] = useState('')
  const [compareLeft, setCompareLeft] = useState('')
  const [compareRight, setCompareRight] = useState('')

  const reloadBootstrap = useCallback(async () => {
    const data = await apiGetJson<BootstrapPayload>(apiBase, '/bootstrap')
    setBootstrap(data)
    setLexiconPath((prev) => prev || data.lexicon_path)
    setText((prev) => (prev ? prev : data.sample_text || ''))
  }, [apiBase])

  useEffect(() => {
    void reloadBootstrap()
  }, [reloadBootstrap])

  useEffect(() => {
    if (!result) return
    void (async () => {
      try {
        const data = await apiGetJson<{ ok: boolean; profile: ProfileRow[] }>(
          apiBase,
          `/domain-profile?language=${language}`,
        )
        if (data.ok && Array.isArray(data.profile)) {
          setProfile(data.profile)
          setSelectedDomain(data.profile[0]?.domain_code ?? '')
        }
      } catch {
        // fallback to basic rows from domain_frequency
        const domainFrequency = result.domain_frequency || {}
        const rows = Object.entries(domainFrequency)
          .map(([domain_code, count]) => ({ domain_code, count }))
          .sort((a, b) => b.count - a.count)
        setProfile(rows)
        setSelectedDomain(rows[0]?.domain_code ?? '')
      }
    })()
  }, [apiBase, language, result])

  const runAnalyze = useCallback(async () => {
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      const payload = {
        text,
        language,
        tokenizer,
        mode,
        min_frequency: minFrequency,
        top_n: topN.trim() === '' ? null : Number(topN),
        lexicon_path: lexiconPath || undefined,
      }
      const data = await apiPostJson<AnalyzeResponse>(apiBase, '/analyze', payload)
      if (!data.ok) {
        setAnalyzeError(data.error.message || data.error.code)
        setResult(null)
        setProfile([])
        return
      }
      setResult(data.result)
      setProfile(data.profile)
      const first = data.profile[0]?.domain_code
      if (typeof first === 'string') {
        setSelectedDomain(first)
      }
    } catch (e) {
      setAnalyzeError(e instanceof Error ? e.message : String(e))
      setResult(null)
      setProfile([])
    } finally {
      setAnalyzing(false)
    }
  }, [apiBase, language, lexiconPath, minFrequency, mode, text, topN, tokenizer])

  const setResultState = useCallback((nextResult: AnalysisResult | null, profileRows?: ProfileRow[]) => {
    setResult(nextResult)
    if (Array.isArray(profileRows)) {
      setProfile(profileRows)
      setSelectedDomain(profileRows[0]?.domain_code ?? '')
      return
    }
    if (!nextResult) {
      setProfile([])
      setSelectedDomain('')
    }
  }, [])

  const value = useMemo<WorkbenchContextValue>(
    () => ({
      apiBase,
      bootstrap,
      reloadBootstrap,
      text,
      setText,
      language,
      setLanguage,
      mode,
      setMode,
      tokenizer,
      setTokenizer,
      minFrequency,
      setMinFrequency,
      topN,
      setTopN,
      lexiconPath,
      setLexiconPath,
      analyzing,
      analyzeError,
      result,
      profile,
      selectedDomain,
      setSelectedDomain,
      keyword,
      setKeyword,
      compareLeft,
      setCompareLeft,
      compareRight,
      setCompareRight,
      runAnalyze,
      setResultState,
    }),
    [
      analyzing,
      analyzeError,
      apiBase,
      bootstrap,
      language,
      lexiconPath,
      minFrequency,
      mode,
      tokenizer,
      profile,
      reloadBootstrap,
      result,
      selectedDomain,
      keyword,
      compareLeft,
      compareRight,
      text,
      topN,
      runAnalyze,
      setResultState,
    ],
  )

  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>
}

export function useWorkbench(): WorkbenchContextValue {
  const ctx = useContext(WorkbenchContext)
  if (!ctx) {
    throw new Error('useWorkbench must be used within WorkbenchProvider')
  }
  return ctx
}
