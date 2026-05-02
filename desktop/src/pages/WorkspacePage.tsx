import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Chip,
  Divider,
  FormControl,
  LinearProgress,
  List,
  ListItemButton,
  ListItemText,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useRef, useState } from 'react'
import { apiPostJson } from '../api/client'
import { useWorkbench } from '../contexts/WorkbenchContext'
import type { AnalysisResult, TokenRow } from '../types/models'
import { getDomainColor } from '../utils/domainColors'
import { useNavigate } from 'react-router-dom'
import { t } from '../i18n'

type RecentFiles = {
  recent_project_files: string[]
  recent_text_files: string[]
  recent_lexicon_files: string[]
}

export function WorkspacePage(): JSX.Element {
  const nav = useNavigate()
  const {
    bootstrap,
    text,
    setText,
    language,
    setLanguage,
    tokenizer,
    setTokenizer,
    mode,
    setMode,
    minFrequency,
    setMinFrequency,
    topN,
    setTopN,
    lexiconPath,
    setLexiconPath,
    analyzing,
    analyzeError,
    runAnalyze,
    result,
    selectedDomain,
    setSelectedDomain,
    apiBase,
    setResultState,
    setKeyword,
    keyword,
    compareLeft,
    compareRight,
    setCompareLeft,
    setCompareRight,
  } = useWorkbench()
  const [tab, setTab] = useState(0)
  const [selectedToken, setSelectedToken] = useState<TokenRow | null>(null)
  const [contextDetail, setContextDetail] = useState<Record<string, unknown> | null>(null)
  const [contextErr, setContextErr] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [recentFiles, setRecentFiles] = useState<RecentFiles>({
    recent_project_files: [],
    recent_text_files: [],
    recent_lexicon_files: [],
  })
  const textFileInputRef = useRef<HTMLInputElement | null>(null)
  const projectFileInputRef = useRef<HTMLInputElement | null>(null)

  const LEMMA_ROWS_LIMIT = 200
  const DOMAIN_ROWS_LIMIT = 200

  const lemmaRows = useMemo(() => {
    if (!result) {
      return { rows: [], truncated: false, total: 0 }
    }
    const entries = Object.entries(result.lemma_frequency || {})
      .map(([lemma, count]) => ({ lemma, count }))
      .sort((a, b) => b.count - a.count)
    return {
      rows: entries.slice(0, LEMMA_ROWS_LIMIT),
      truncated: entries.length > LEMMA_ROWS_LIMIT,
      total: entries.length,
    }
  }, [result])

  const domainRows = useMemo(() => {
    if (!result) {
      return { rows: [], truncated: false, total: 0 }
    }
    const entries = Object.entries(result.domain_frequency || {})
      .map(([domain, count]) => ({ domain, count }))
      .sort((a, b) => b.count - a.count)
    return {
      rows: entries.slice(0, DOMAIN_ROWS_LIMIT),
      truncated: entries.length > DOMAIN_ROWS_LIMIT,
      total: entries.length,
    }
  }, [result])

  const wsdStatus = useMemo(() => {
    const wsd = (result as AnalysisResult | null)?.wsd
    if (!wsd) {
      return null
    }
    const enabled = Boolean(wsd.enabled)
    const applied = Number(wsd.applied_tokens || 0)
    const modelDir = String(wsd.model_dir || '')
    const reason = String(wsd.fallback_reason || '')
    return { enabled, applied, modelDir, reason }
  }, [result])
  const layerStatus = useMemo(() => {
    const layers = (result as AnalysisResult | null)?.layers
    if (!layers) return null
    return {
      l1Hit: Number(layers.layer1_dictionary_hits || 0),
      l1Miss: Number(layers.layer1_dictionary_misses || 0),
      l1Wn: Number(layers.layer1_wordnet_backfill_hits || 0),
      l2: Number(layers.layer2_vector_hits || 0),
      l3: Number(layers.layer3_adjudications || 0),
      mrw: Number(layers.layer2_mrw_candidates || 0),
      mipvu: Number(layers.layer3_mipvu_tokens || 0),
    }
  }, [result])

  const resolveDomainLabel = (code: string): string => {
    const cats = bootstrap?.categories || {}
    const info = (cats as Record<string, Record<string, string>>)[code]
    if (!info) {
      return code
    }
    if (language === 'en') {
      return info.en || code
    }
    return info[language] || code
  }

  const renderDomainText = (tok: TokenRow): string => {
    const codes = Array.isArray(tok.domain_codes) && tok.domain_codes.length ? tok.domain_codes : [String(tok.domain_code || '')]
    const normalized = codes.map((c) => String(c || '').trim()).filter(Boolean)
    if (!normalized.length) {
      return t(language as never, 'na')
    }
    const labels = normalized.map((c) => resolveDomainLabel(c))
    return `${normalized.join(' / ')} (${labels.join(' / ')})`
  }

  const renderDomainCodeText = (codeRaw: unknown): string => {
    const code = String(codeRaw || '').trim()
    if (!code) return t(language as never, 'na')
    return `${code} (${resolveDomainLabel(code)})`
  }

  const loadContext = async (token: TokenRow) => {
    setSelectedToken(token)
    setContextErr(null)
    setContextDetail(null)
    try {
      const offset = Number(token.offset ?? 0)
      const key = String(token.surface || token.lemma || '')
      const data = await apiPostJson<Record<string, unknown>>(apiBase, '/context-detail', {
        offset,
        key,
      })
      setContextDetail(data)
    } catch (e) {
      setContextErr(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    if (!window.wmatrixDesktop?.getRecentFiles) {
      return
    }
    void window.wmatrixDesktop.getRecentFiles().then((data) => {
      setRecentFiles({
        recent_project_files: Array.isArray(data.recent_project_files) ? (data.recent_project_files as string[]) : [],
        recent_text_files: Array.isArray(data.recent_text_files) ? (data.recent_text_files as string[]) : [],
        recent_lexicon_files: Array.isArray(data.recent_lexicon_files) ? (data.recent_lexicon_files as string[]) : [],
      })
    })
  }, [])

  const saveRecent = async (kind: 'project' | 'text', value: string) => {
    if (!value.trim()) {
      return
    }
    const key = kind === 'project' ? 'recent_project_files' : 'recent_text_files'
    const prev = recentFiles[key]
    const nextList = [value, ...prev.filter((x) => x !== value)].slice(0, 10)
    const next: RecentFiles = { ...recentFiles, [key]: nextList }
    setRecentFiles(next)
    if (window.wmatrixDesktop?.setRecentFiles) {
      await window.wmatrixDesktop.setRecentFiles(next as unknown as Record<string, unknown>)
    }
  }

  const persistRecent = async (next: RecentFiles) => {
    setRecentFiles(next)
    if (window.wmatrixDesktop?.setRecentFiles) {
      await window.wmatrixDesktop.setRecentFiles(next as unknown as Record<string, unknown>)
    }
  }

  const clearRecent = async (kind: 'project' | 'text' | 'all') => {
    const next: RecentFiles = {
      ...recentFiles,
      recent_project_files: kind === 'text' ? recentFiles.recent_project_files : [],
      recent_text_files: kind === 'project' ? recentFiles.recent_text_files : [],
      recent_lexicon_files: recentFiles.recent_lexicon_files,
    }
    await persistRecent(next)
    setActionMsg(t(language as never, 'recentCleared'))
  }

  const pruneMissingRecent = async (kind: 'project' | 'text') => {
    const key = kind === 'project' ? 'recent_project_files' : 'recent_text_files'
    const list = recentFiles[key]
    if (!window.wmatrixDesktop?.pathExists) {
      setActionMsg(t(language as never, 'recentPathCheckUnavailable'))
      return
    }
    const checks = await Promise.all(list.map((p) => window.wmatrixDesktop!.pathExists(p)))
    const kept = list.filter((_, i) => checks[i]?.exists)
    const removedCount = list.length - kept.length
    if (removedCount <= 0) {
      setActionMsg(t(language as never, 'recentNoMissing'))
      return
    }
    const next: RecentFiles = { ...recentFiles, [key]: kept }
    await persistRecent(next)
    setActionMsg(`${t(language as never, 'recentPruned')}: ${removedCount}`)
  }

  const applyProjectPayload = async (payload: Record<string, unknown>, loadedFrom: string) => {
    const settings = (payload.settings || {}) as Record<string, unknown>
    const texts = (payload.texts || {}) as Record<string, unknown>
    const results = (payload.results || {}) as Record<string, unknown>
    setLanguage(String(settings.language || language))
    setTokenizer(String(settings.tokenizer || tokenizer))
    setMode(String(settings.mode || mode))
    setMinFrequency(Number(settings.minFrequency || minFrequency))
    setTopN(String(settings.topN || ''))
    setLexiconPath(String(settings.lexiconPath || lexiconPath))
    setSelectedDomain(String(settings.selectedDomain || ''))
    setKeyword(String(settings.keyword || ''))
    setText(String(texts.primary || ''))
    const loaded = (results.primary || null) as Record<string, unknown> | null
    setCompareLeft(String(results.compareLeft || ''))
    setCompareRight(String(results.compareRight || ''))
    if (loaded && Array.isArray((loaded as AnalysisResult).tokens)) {
      setResultState(loaded as never)
    } else if (loaded) {
      setActionMsg(t(language as never, 'projectFormatInvalid'))
    }
    await saveRecent('project', loadedFrom)
    setActionMsg(`${t(language as never, 'projectLoaded')}: ${loadedFrom}`)
  }

  const formatOpenError = (raw: string | undefined, fallback: string, kind: 'text' | 'project') => {
    const msg = String(raw || '').toLowerCase()
    if (msg.includes('enoent')) {
      return `${t(language as never, 'recentMissingFile')}: ${fallback}`
    }
    if (msg.includes('eacces') || msg.includes('eperm')) {
      return `${t(language as never, 'recentPermissionDenied')}: ${fallback}`
    }
    return `${t(language as never, kind === 'text' ? 'textLoadFailed' : 'projectLoadFailed')}: ${raw || fallback}`
  }

  const saveProject = async () => {
    if (!window.wmatrixDesktop?.saveFile) {
      setActionMsg(t(language as never, 'saveOnlyElectron'))
      return
    }
    const payload = {
      settings: { language, tokenizer, mode, minFrequency, topN, lexiconPath, selectedDomain, keyword, view: 'workspace' },
      texts: { primary: text },
      results: { primary: result, compareLeft, compareRight },
    }
    const ts = new Date().toISOString().replace(/[:.]/g, '-')
    const suggested = `bunseki-project-${ts}.wmja.json`
    const res = await window.wmatrixDesktop.saveFile(suggested, JSON.stringify(payload, null, 2))
    if (res.canceled) {
      return
    }
    await saveRecent('project', res.path || suggested)
    setActionMsg(`${t(language as never, 'projectSaved')}: ${res.path || suggested}`)
  }

  const loadProjectFile = async (file: File) => {
    try {
      const payload = JSON.parse(await file.text()) as Record<string, unknown>
      await applyProjectPayload(payload, file.name)
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e)
      setActionMsg(`${t(language as never, 'projectFormatInvalid')}: ${m}`)
    }
  }

  const loadTextFile = async (file: File) => {
    try {
      const content = await file.text()
      setText(content)
      await saveRecent('text', file.name)
      setActionMsg(`${t(language as never, 'textLoaded')}: ${file.name}`)
    } catch (e) {
      setActionMsg(`${t(language as never, 'textLoadFailed')}: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  const openTextViaDialog = async () => {
    if (!window.wmatrixDesktop?.openTextFile) {
      textFileInputRef.current?.click()
      return
    }
    const res = await window.wmatrixDesktop.openTextFile()
    if (res.canceled || !res.content) {
      return
    }
    setText(res.content)
    await saveRecent('text', res.path || '')
    setActionMsg(`${t(language as never, 'textLoaded')}: ${res.path || ''}`)
  }

  const openProjectViaDialog = async () => {
    if (!window.wmatrixDesktop?.openProjectFile) {
      projectFileInputRef.current?.click()
      return
    }
    const res = await window.wmatrixDesktop.openProjectFile()
    if (res.canceled || !res.content) {
      return
    }
    try {
      const payload = JSON.parse(res.content) as Record<string, unknown>
      await applyProjectPayload(payload, res.path || '')
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e)
      setActionMsg(`${t(language as never, 'projectFormatInvalid')}: ${m}`)
    }
  }

  const openRecentText = async (filePath: string) => {
    if (!window.wmatrixDesktop?.openTextPath) {
      textFileInputRef.current?.click()
      return
    }
    const res = await window.wmatrixDesktop.openTextPath(filePath)
    if (res.canceled || typeof res.content !== 'string') {
      setActionMsg(formatOpenError(res.error, filePath, 'text'))
      return
    }
    setText(res.content)
    await saveRecent('text', res.path || filePath)
    setActionMsg(`${t(language as never, 'textLoaded')}: ${res.path || filePath}`)
  }

  const openRecentProject = async (filePath: string) => {
    if (!window.wmatrixDesktop?.openProjectPath) {
      projectFileInputRef.current?.click()
      return
    }
    const res = await window.wmatrixDesktop.openProjectPath(filePath)
    if (res.canceled || typeof res.content !== 'string') {
      setActionMsg(formatOpenError(res.error, filePath, 'project'))
      return
    }
    try {
      const payload = JSON.parse(res.content) as Record<string, unknown>
      await applyProjectPayload(payload, res.path || filePath)
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e)
      setActionMsg(`${t(language as never, 'projectFormatInvalid')}: ${m}`)
    }
  }

  const exportCsv = async () => {
    if (!result) {
      return
    }
    const lines = ['record_type,surface,lemma,pos,domain_code,key,count']
    for (const tok of result.tokens || []) {
      lines.push(
        `token,"${String(tok.surface || '').replace(/"/g, '""')}","${String(tok.lemma || '').replace(/"/g, '""')}","${String(tok.pos || '').replace(/"/g, '""')}","${String(tok.domain_code || '').replace(/"/g, '""')}",,`,
      )
    }
    for (const [lemma, count] of Object.entries(result.lemma_frequency || {})) {
      lines.push(`lemma_frequency,,,,,"${lemma.replace(/"/g, '""')}",${count}`)
    }
    for (const [domain, count] of Object.entries(result.domain_frequency || {})) {
      lines.push(`domain_frequency,,,,"${domain.replace(/"/g, '""')}","${domain.replace(/"/g, '""')}",${count}`)
    }
    const content = lines.join('\n')
    if (window.wmatrixDesktop?.saveFile) {
      const res = await window.wmatrixDesktop.saveFile('analysis.csv', content)
      if (!res.canceled) {
        setActionMsg(`${t(language as never, 'exportedCsv')}: ${res.path || 'analysis.csv'}`)
      }
      return
    }
    setActionMsg(t(language as never, 'exportOnlyElectron'))
  }

  const exportJson = async () => {
    if (!result) {
      return
    }
    if (!window.wmatrixDesktop?.saveFile) {
      setActionMsg(t(language as never, 'exportOnlyElectron'))
      return
    }
    const res = await window.wmatrixDesktop.saveFile('analysis.json', JSON.stringify(result, null, 2))
    if (!res.canceled) {
      setActionMsg(`${t(language as never, 'exportedJson')}: ${res.path || 'analysis.json'}`)
    }
  }

  const exportBundle = async () => {
    if (!result) {
      return
    }
    const tokenLines = ['surface,lemma,pos,domain_code']
    for (const tok of result.tokens || []) {
      tokenLines.push(
        `"${String(tok.surface || '').replace(/"/g, '""')}","${String(tok.lemma || '').replace(/"/g, '""')}","${String(tok.pos || '').replace(/"/g, '""')}","${String(tok.domain_code || '').replace(/"/g, '""')}"`,
      )
    }
    const lemmaLines = ['lemma,count']
    for (const [lemma, count] of Object.entries(result.lemma_frequency || {})) {
      lemmaLines.push(`"${lemma.replace(/"/g, '""')}",${count}`)
    }
    const domainLines = ['domain_code,count']
    for (const [domain, count] of Object.entries(result.domain_frequency || {})) {
      domainLines.push(`"${domain.replace(/"/g, '""')}",${count}`)
    }
    if (!window.wmatrixDesktop?.saveFile) {
      setActionMsg(t(language as never, 'exportOnlyElectron'))
      return
    }
    const bundle = {
      tokens_csv: tokenLines.join('\n'),
      lemma_frequency_csv: lemmaLines.join('\n'),
      domain_frequency_csv: domainLines.join('\n'),
    }
    const res = await window.wmatrixDesktop.saveFile('analysis.bundle.json', JSON.stringify(bundle, null, 2))
    if (!res.canceled) {
      setActionMsg(`${t(language as never, 'exportedBundle')}: ${res.path || 'analysis.bundle.json'}`)
    }
  }

  useEffect(() => {
    const handler = (evt: Event) => {
      const action = (evt as CustomEvent<string>).detail
      if (action === 'file.openText') void openTextViaDialog()
      if (action === 'file.openProject') void openProjectViaDialog()
      if (action === 'file.saveProject') void saveProject()
      if (action === 'file.exportCsv') void exportCsv()
      if (action === 'file.exportJson') void exportJson()
      if (action === 'file.exportBundle') void exportBundle()
      if (action === 'tools.analyze') void runAnalyze()
    }
    window.addEventListener('bunseki:menu-action', handler)
    return () => window.removeEventListener('bunseki:menu-action', handler)
  }, [runAnalyze])

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'workspaceTitle')}</Typography>
      {bootstrap?.help ? (
        <Alert severity="info" variant="outlined">
          {bootstrap.help}
        </Alert>
      ) : null}
      <TextField
        label={t(language as never, 'lexiconPath')}
        value={lexiconPath}
        onChange={(e) => setLexiconPath(e.target.value)}
        fullWidth
        size="small"
      />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>{t(language as never, 'uiLabels')}</InputLabel>
          <Select
            label={t(language as never, 'uiLabels')}
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <MenuItem value="ja">日本語</MenuItem>
            <MenuItem value="zh">中文</MenuItem>
            <MenuItem value="en">English</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>{t(language as never, 'tokenizer')}</InputLabel>
          <Select
            label={t(language as never, 'tokenizer')}
            value={tokenizer}
            onChange={(e) => setTokenizer(String(e.target.value))}
          >
            <MenuItem value="sudachi">SudachiPy</MenuItem>
            <MenuItem value="mecab">MeCab</MenuItem>
            <MenuItem value="chasen">ChaSen (MeCab -Ochasen)</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>{t(language as never, 'sudachiMode')}</InputLabel>
          <Select label={t(language as never, 'sudachiMode')} value={mode} onChange={(e) => setMode(e.target.value)}>
            <MenuItem value="A">A</MenuItem>
            <MenuItem value="B">B</MenuItem>
            <MenuItem value="C">C</MenuItem>
          </Select>
        </FormControl>
        <TextField
          label={t(language as never, 'minFrequency')}
          type="number"
          size="small"
          value={minFrequency}
          onChange={(e) => {
            const v = Number(e.target.value)
            setMinFrequency(Number.isNaN(v) ? 0 : v)
          }}
          sx={{ width: 140 }}
        />
        <TextField
          label={t(language as never, 'topNLemmas')}
          size="small"
          value={topN}
          onChange={(e) => setTopN(e.target.value)}
          sx={{ width: 180 }}
        />
      </Stack>
      <TextField
        label={t(language as never, 'japaneseText')}
        value={text}
        onChange={(e) => setText(e.target.value)}
        multiline
        minRows={12}
        fullWidth
      />
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} useFlexGap flexWrap="wrap" alignItems="center">
        <Button variant="contained" size="large" onClick={() => void runAnalyze()} disabled={analyzing}>
          {analyzing ? t(language as never, 'analyzing') : t(language as never, 'analyze')}
        </Button>
        <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
        <ButtonGroup variant="outlined" size="small">
          <Button onClick={() => void openTextViaDialog()}>{t(language as never, 'openTextFile')}</Button>
          <Button onClick={() => void openProjectViaDialog()}>{t(language as never, 'openProject')}</Button>
          <Button onClick={saveProject}>{t(language as never, 'saveProject')}</Button>
        </ButtonGroup>
        <ButtonGroup variant="outlined" size="small">
          <Button onClick={() => { setCompareLeft(text); nav('/compare') }}>{t(language as never, 'setCompareLeft')}</Button>
          <Button onClick={() => { setCompareRight(text); nav('/compare') }}>{t(language as never, 'setCompareRight')}</Button>
        </ButtonGroup>
        <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
        <ButtonGroup variant="outlined" size="small">
          <Button onClick={() => void exportCsv()} disabled={!result}>{t(language as never, 'exportCsv')}</Button>
          <Button onClick={() => void exportJson()} disabled={!result}>{t(language as never, 'exportJson')}</Button>
          <Button onClick={exportBundle} disabled={!result}>{t(language as never, 'exportBundle')}</Button>
        </ButtonGroup>
      </Stack>
      {analyzing ? <LinearProgress sx={{ mt: 1 }} /> : null}
      <input
        ref={textFileInputRef}
        type="file"
        hidden
        accept=".txt,.md,.csv,.json"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) {
            void loadTextFile(f)
          }
          e.target.value = ''
        }}
      />
      <input
        ref={projectFileInputRef}
        type="file"
        hidden
        accept=".wmja.json,.json"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) {
            void loadProjectFile(f)
          }
          e.target.value = ''
        }}
      />
      {actionMsg ? <Alert severity="info">{actionMsg}</Alert> : null}
      {analyzeError ? <Alert severity="error">{analyzeError}</Alert> : null}
      {(recentFiles.recent_project_files.length > 0 || recentFiles.recent_text_files.length > 0) && (
        <Paper sx={{ p: 1 }}>
          <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2}>
            <Box sx={{ minWidth: 260 }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Typography variant="subtitle2">{t(language as never, 'recentProjects')}</Typography>
                <Stack direction="row" spacing={0.5}>
                  <Button size="small" onClick={() => void pruneMissingRecent('project')}>{t(language as never, 'pruneMissing')}</Button>
                  <Button size="small" onClick={() => void clearRecent('project')}>{t(language as never, 'clear')}</Button>
                </Stack>
              </Stack>
              <List dense>
                {recentFiles.recent_project_files.map((name) => (
                  <ListItemButton key={name} onClick={() => void openRecentProject(name)}>
                    <ListItemText primary={name} />
                  </ListItemButton>
                ))}
              </List>
            </Box>
            <Box sx={{ minWidth: 260 }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Typography variant="subtitle2">{t(language as never, 'recentTextFiles')}</Typography>
                <Stack direction="row" spacing={0.5}>
                  <Button size="small" onClick={() => void pruneMissingRecent('text')}>{t(language as never, 'pruneMissing')}</Button>
                  <Button size="small" onClick={() => void clearRecent('text')}>{t(language as never, 'clear')}</Button>
                </Stack>
              </Stack>
              <List dense>
                {recentFiles.recent_text_files.map((name) => (
                  <ListItemButton key={name} onClick={() => void openRecentText(name)}>
                    <ListItemText primary={name} />
                  </ListItemButton>
                ))}
              </List>
            </Box>
          </Stack>
          <Stack direction="row" justifyContent="flex-end">
            <Button size="small" onClick={() => void clearRecent('all')}>{t(language as never, 'clearAllRecent')}</Button>
          </Stack>
        </Paper>
      )}
      {result ? (
        <>
          <Alert severity="success" variant="outlined">
            {t(language as never, 'analysisComplete')} - {t(language as never, 'tokensCount')}:&nbsp;
            {String(result.summary?.token_count ?? '')}, {t(language as never, 'uniqueLemmas')}:&nbsp;
            {String(result.summary?.unique_lemma_count ?? '')}
          </Alert>
          {wsdStatus ? (
            <Alert severity={wsdStatus.enabled ? 'info' : 'warning'} variant="outlined">
              BERT-WSD: {wsdStatus.enabled ? 'enabled' : 'disabled'} | applied_tokens: {String(wsdStatus.applied)} | model: {wsdStatus.modelDir || 'N/A'}
              {wsdStatus.reason ? ` | reason: ${wsdStatus.reason}` : ''}
            </Alert>
          ) : null}
          {layerStatus ? (
            <Alert severity="info" variant="outlined">
              Layers: L1(hit/miss)={layerStatus.l1Hit}/{layerStatus.l1Miss} | L1-WordNet(backfill)={layerStatus.l1Wn} | L2(vector)={layerStatus.l2} | L2(MRW candidates)={layerStatus.mrw} | L3(adjudication)={layerStatus.l3} | L3(MIPVU tokens)={layerStatus.mipvu}
            </Alert>
          ) : null}
          <Paper>
            <Tabs value={tab} onChange={(_, next) => setTab(next)} variant="scrollable">
              <Tab label={t(language as never, 'tabTokens')} />
              <Tab label={t(language as never, 'tabLemmaFrequency')} />
              <Tab label={t(language as never, 'tabDomainFrequency')} />
            </Tabs>
          </Paper>
          {tab === 0 ? (
            <Table size="small" component={Paper}>
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  <TableCell>{t(language as never, 'surface')}</TableCell>
                  <TableCell>{t(language as never, 'lemma')}</TableCell>
                  <TableCell>源域</TableCell>
                  <TableCell>目标域</TableCell>
                  <TableCell>MRW</TableCell>
                  <TableCell>MIPVU</TableCell>
                  <TableCell>{t(language as never, 'pos')}</TableCell>
                  <TableCell align="right">{t(language as never, 'offset')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(result.tokens || []).slice(0, 500).map((tok, idx) => (
                  <TableRow
                    key={`${idx}-${String(tok.surface || '')}`}
                    hover
                    selected={selectedToken === tok}
                    sx={{ cursor: 'pointer' }}
                    onClick={() => {
                      setSelectedDomain(String(tok.domain_code || ''))
                      void loadContext(tok)
                    }}
                  >
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell>{String(tok.surface || '')}</TableCell>
                    <TableCell>{String(tok.lemma || '')}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={renderDomainCodeText(tok.source_domain_label || tok.domain_code)}
                        sx={{
                          bgcolor: getDomainColor(String(tok.source_domain_label || tok.domain_code || '')),
                          color: '#fff',
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      {tok.target_domain_label ? (
                        <Chip
                          size="small"
                          label={renderDomainCodeText(tok.target_domain_label)}
                          sx={{
                            bgcolor: getDomainColor(String(tok.target_domain_label || 'Z99')),
                            color: '#fff',
                          }}
                        />
                      ) : (
                        <Typography variant="body2" color="text.secondary">—</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {tok.is_metaphor_candidate ? (
                        <Chip size="small" color="warning" label={`cand ${Number(tok.mrw_distance || 0).toFixed(3)}`} />
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          {Number(tok.mrw_distance || 0).toFixed(3)}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {tok.mipvu_path ? (
                        <Chip
                          size="small"
                          color={String(tok.mipvu_path || '').includes('llm_confirm') ? 'success' : String(tok.mipvu_path || '').includes('llm_failed') ? 'error' : 'default'}
                          label={String(tok.mipvu_path || '')}
                        />
                      ) : (
                        <Typography variant="body2" color="text.secondary">—</Typography>
                      )}
                    </TableCell>
                    <TableCell>{String(tok.pos || '')}</TableCell>
                    <TableCell align="right">{String(tok.offset ?? '')}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
          {tab === 1 ? (
            <>
            <Table size="small" component={Paper}>
              <TableHead>
                <TableRow>
                  <TableCell>{t(language as never, 'lemma')}</TableCell>
                  <TableCell align="right">{t(language as never, 'tableCount')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {lemmaRows.rows.map((row) => (
                  <TableRow
                    key={row.lemma}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => {
                      setKeyword(row.lemma)
                      nav('/kwic')
                    }}
                  >
                    <TableCell>{row.lemma}</TableCell>
                    <TableCell align="right">{row.count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {lemmaRows.truncated ? (
              <Alert severity="info" sx={{ mt: 1 }}>
                Showing top {LEMMA_ROWS_LIMIT} of {lemmaRows.total} lemmas.
              </Alert>
            ) : null}
            </>
          ) : null}
          {tab === 2 ? (
            <>
            <Table size="small" component={Paper}>
              <TableHead>
                <TableRow>
                  <TableCell>{t(language as never, 'domain')}</TableCell>
                  <TableCell align="right">{t(language as never, 'tableCount')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {domainRows.rows.map((row) => (
                  <TableRow
                    key={row.domain}
                    hover
                    selected={row.domain === selectedDomain}
                    sx={{ cursor: 'pointer' }}
                    onClick={() => setSelectedDomain(row.domain)}
                  >
                    <TableCell>{row.domain}</TableCell>
                    <TableCell align="right">{row.count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {domainRows.truncated ? (
              <Alert severity="info" sx={{ mt: 1 }}>
                Showing top {DOMAIN_ROWS_LIMIT} of {domainRows.total} domains.
              </Alert>
            ) : null}
            </>
          ) : null}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <Button
              size="small"
              variant="outlined"
              disabled={!selectedDomain}
              onClick={() => nav('/profile')}
            >
              {t(language as never, 'openProfile')}
            </Button>
            <Button
              size="small"
              variant="outlined"
              disabled={!selectedDomain}
              onClick={() => nav('/lexicon')}
            >
              {t(language as never, 'openLexiconSelectedDomain')}
            </Button>
            <Button
              size="small"
              variant="outlined"
              onClick={() => {
                setKeyword(selectedToken?.lemma || selectedToken?.surface || '')
                nav('/kwic')
              }}
              disabled={!selectedToken}
            >
              {t(language as never, 'openKwicSelectedToken')}
            </Button>
          </Stack>
          {(selectedToken || contextDetail || contextErr) && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                {t(language as never, 'contextDetailTitle')}
              </Typography>
              {selectedToken ? (
                <Typography variant="body2" sx={{ mb: 1 }}>
                  {t(language as never, 'token')}: {String(selectedToken.surface || '')} ({String(selectedToken.lemma || '')}) /{' '}
                  {t(language as never, 'domain')}: {renderDomainText(selectedToken)}
                </Typography>
              ) : null}
              {selectedToken ? (
                <Stack spacing={0.75} sx={{ mb: 1 }}>
                  {selectedToken.basic_meaning ? (
                    <Typography variant="body2">
                      <b>basic_meaning:</b> {String(selectedToken.basic_meaning)}
                    </Typography>
                  ) : null}
                  {selectedToken.source_domain_label ? (
                    <Typography variant="body2">
                      <b>source_domain_label:</b> {String(selectedToken.source_domain_label)}
                      {selectedToken.layer1_source ? ` (${String(selectedToken.layer1_source)})` : ''}
                    </Typography>
                  ) : null}
                  {selectedToken.mrw_distance !== undefined ? (
                    <Typography variant="body2">
                      <b>mrw_distance:</b> {Number(selectedToken.mrw_distance || 0).toFixed(4)}{' '}
                      {selectedToken.is_metaphor_candidate ? '(candidate)' : ''}
                    </Typography>
                  ) : null}
                  {selectedToken.mipvu_path !== undefined ? (
                    <Typography variant="body2">
                      <b>mipvu_path:</b>{' '}
                      <Chip
                        size="small"
                        color={String(selectedToken.mipvu_path || '').includes('llm_confirm') ? 'success' : String(selectedToken.mipvu_path || '').includes('llm_failed') ? 'error' : 'default'}
                        label={String(selectedToken.mipvu_path || '')}
                      />
                    </Typography>
                  ) : null}
                  {selectedToken.is_metaphor !== undefined ? (
                    <Typography variant="body2">
                      <b>is_metaphor:</b> {selectedToken.is_metaphor ? 'True' : 'False'}
                    </Typography>
                  ) : null}
                  {selectedToken.source_domain ? (
                    <Typography variant="body2">
                      <b>source_domain (LLM refined):</b> {String(selectedToken.source_domain)}
                    </Typography>
                  ) : null}
                  {selectedToken.target_domain ? (
                    <Typography variant="body2">
                      <b>target_domain:</b> {String(selectedToken.target_domain)}
                    </Typography>
                  ) : null}
                  {selectedToken.target_domain_label ? (
                    <Typography variant="body2">
                      <b>target_domain_label:</b> {String(selectedToken.target_domain_label)}
                    </Typography>
                  ) : null}
                  {selectedToken.confidence ? (
                    <Typography variant="body2">
                      <b>confidence:</b> {String(selectedToken.confidence)}
                    </Typography>
                  ) : null}
                  {/* Also show token_mipvu from context-detail API response for cross-ref */}
                  {contextDetail && (contextDetail as Record<string, unknown>).token_mipvu ? (
                    <Paper variant="outlined" sx={{ p: 1, bgcolor: '#fafbfc' }}>
                      <Typography variant="caption" color="text.secondary">
                        API token_mipvu
                      </Typography>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 11 }}>
                        {JSON.stringify((contextDetail as Record<string, unknown>).token_mipvu, null, 2)}
                      </pre>
                    </Paper>
                  ) : null}
                </Stack>
              ) : null}
              {contextErr ? <Alert severity="error">{contextErr}</Alert> : null}
              {contextDetail ? (
                <Stack spacing={1}>
                  {contextDetail.snippet !== undefined && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">{t(language as never, 'contextSnippet')}</Typography>
                      <Paper variant="outlined" sx={{ p: 1.5, mt: 0.5, fontFamily: 'monospace', fontSize: 14, lineHeight: 1.7, bgcolor: '#fafbfc' }}>
                        {String(contextDetail.snippet || '')}
                      </Paper>
                    </Box>
                  )}
                  {contextDetail.highlight_start !== undefined && (
                    <Stack direction="row" spacing={3}>
                      <Typography variant="body2">
                        <b>{t(language as never, 'offset')}:</b> {String(contextDetail.start ?? '')}–{String(contextDetail.end ?? '')}
                      </Typography>
                      <Typography variant="body2">
                        <b>{t(language as never, 'highlight')}:</b> {String(contextDetail.highlight_start)}–{String(contextDetail.highlight_end)}
                      </Typography>
                    </Stack>
                  )}
                </Stack>
              ) : null}
            </Paper>
          )}
        </>
      ) : null}
    </Stack>
  )
}
