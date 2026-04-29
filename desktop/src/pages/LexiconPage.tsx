import {
  Alert,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useRef, useState } from 'react'
import { apiGetJson, apiPostJson } from '../api/client'
import { useWorkbench } from '../contexts/WorkbenchContext'
import { getDomainColor } from '../utils/domainColors'
import type { LexiconDomainRow } from '../types/models'
import { useLocation, useNavigate } from 'react-router-dom'
import { t } from '../i18n'

type Overview = { domains: LexiconDomainRow[]; path: string }

export function LexiconPage(): JSX.Element {
  const nav = useNavigate()
  const location = useLocation()
  const { apiBase, reloadBootstrap, result, selectedDomain, setSelectedDomain, setKeyword, setLexiconPath, language } =
    useWorkbench()
  const [overview, setOverview] = useState<Overview | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [domainCode, setDomainCode] = useState(selectedDomain || '')
  const [lemma, setLemma] = useState('')
  const [moveToDomain, setMoveToDomain] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [bulkText, setBulkText] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmAction, setConfirmAction] = useState<{ title: string; text: string; onConfirm: () => void } | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const loadOverview = useCallback(() => {
    apiGetJson<Overview>(apiBase, '/lexicon/overview')
      .then(setOverview)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : String(e)))
  }, [apiBase])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  useEffect(() => {
    setDomainCode((prev) => prev || selectedDomain || '')
  }, [selectedDomain])

  useEffect(() => {
    const q = new URLSearchParams(location.search).get('domain')
    if (q) {
      setDomainCode(q)
      setSelectedDomain(q)
    }
    // only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const addTerm = async () => {
    const d = domainCode.trim() || 'Z99'
    const l = lemma.trim()
    if (!l) return
    try {
      const res = await apiPostJson<{ ok: boolean; added: number }>(apiBase, '/lexicon/add', {
        items: [{ domain_code: d, lemma: l }],
      })
      if (!res.ok) {
        setMsg(`${t(language as never, 'addFailed')}`)
        return
      }
      setLemma('')
      setMsg(`${t(language as never, 'addedTerms')}: ${res.added}`)
      loadOverview()
    } catch (e) {
      setMsg(`${t(language as never, 'addFailed')}: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  const showConfirm = (title: string, text: string, onConfirm: () => void) => {
    setConfirmAction({ title, text, onConfirm })
    setConfirmOpen(true)
  }

  const removeTerm = async () => {
    const d = domainCode.trim() || 'Z99'
    const l = lemma.trim()
    if (!l) return
    try {
      const res = await apiPostJson<{ ok: boolean; removed: number }>(apiBase, '/lexicon/remove-term', {
        domain_code: d,
        lemma: l,
      })
      if (!res.ok) {
        setMsg(`${t(language as never, 'removeTermFailed')}`)
        return
      }
      setMsg(`${t(language as never, 'removedTerms')}: ${res.removed}`)
      loadOverview()
    } catch (e) {
      setMsg(`${t(language as never, 'removeTermFailed')}: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  const moveTerm = async () => {
    const d = domainCode.trim() || 'Z99'
    const l = lemma.trim()
    const target = moveToDomain.trim()
    if (!l || !target) return
    try {
      const res = await apiPostJson<{ ok: boolean }>(apiBase, '/lexicon/move-term', {
        from_domain: d,
        to_domain: target,
        lemma: l,
      })
      if (!res.ok) {
        setMsg(t(language as never, "moveTermFailed"))
        return
      }
      setMoveToDomain('')
      setMsg(t(language as never, "movedTerm"))
      loadOverview()
    } catch (e) {
      setMsg(t(language as never, "moveTermFailed") + ": " + (e instanceof Error ? e.message : String(e)))
    }
  }

  const removeDomain = async () => {
    const d = domainCode.trim()
    if (!d) return
    try {
      const res = await apiPostJson<{ ok: boolean; removed: number }>(apiBase, '/lexicon/remove-domain', {
        domain_code: d,
      })
      if (!res.ok) {
        setMsg(`${t(language as never, 'removeDomainFailed')}`)
        return
      }
      setDomainCode('')
      setMsg(`${t(language as never, 'removedDomain')}: ${res.removed}`)
      loadOverview()
    } catch (e) {
      setMsg(`${t(language as never, 'removeDomainFailed')}: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  const addBulk = async (source?: string) => {
    const raw = source || bulkText
    if (!raw.trim()) return
    const items: Array<{ domain_code: string; lemma: string }> = []
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = line.trim()
      if (!trimmed) continue
      const parts = trimmed.split(/[\t,:]/)
      if (parts.length >= 2) {
        items.push({ domain_code: parts[0].trim(), lemma: parts.slice(1).join(',').trim() })
      } else {
        items.push({ domain_code: domainCode.trim() || 'Z99', lemma: trimmed })
      }
    }
    if (!items.length) {
      setMsg(t(language as never, 'noBulkEntries'))
      return
    }
    try {
      const res = await apiPostJson<{ ok: boolean; added: number }>(apiBase, '/lexicon/add', { items })
      if (!res.ok) {
        setMsg(`${t(language as never, 'bulkAddFailed')}`)
        return
      }
      setBulkText('')
      setMsg(`${t(language as never, 'bulkImported')}: ${res.added}`)
      loadOverview()
    } catch (e) {
      setMsg(`${t(language as never, 'bulkAddFailed')}: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  const importAnalyzedLemmas = async (selectedOnly: boolean) => {
    if (!result) {
      setMsg(t(language as never, 'runAnalyzeFirstForImport'))
      return
    }
    const items: Array<{ domain_code: string; lemma: string }> = []
    const targetDomain = selectedDomain || ''
    for (const tok of result.tokens || []) {
      const code = selectedOnly && targetDomain ? targetDomain : (String(tok.domain_code || '') || 'Z99')
      if (!selectedOnly && !String(tok.domain_code || '')) continue
      const tokLemma = String(tok.lemma || '').trim()
      if (!tokLemma) continue
      items.push({ domain_code: code, lemma: tokLemma })
    }
    if (!items.length) {
      setMsg(t(language as never, 'noLemmasForImport'))
      return
    }
    try {
      const res = await apiPostJson<{ ok: boolean; added: number }>(apiBase, '/lexicon/add', { items })
      if (!res.ok) {
        setMsg(`${t(language as never, 'bulkAddFailed')}`)
        return
      }
      setMsg(`${t(language as never, 'bulkImported')}: ${res.added}`)
      loadOverview()
    } catch (e) {
      setMsg(`${t(language as never, 'bulkAddFailed')}: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  const saveLexiconAs = async () => {
    if (!window.wmatrixDesktop?.saveFile) {
      setMsg(t(language as never, 'saveLexiconOnlyElectron'))
      return
    }
    try {
      const raw = await apiGetJson<Record<string, unknown>>(apiBase, '/lexicon/raw')
      const res = await window.wmatrixDesktop.saveFile('lexicon.json', JSON.stringify(raw, null, 2))
      if (!res.canceled) {
        setMsg(`${t(language as never, 'lexiconSnapshotSaved')}: ${res.path || 'lexicon.json'}`)
      }
    } catch (e) {
      setMsg(t(language as never, 'saveLexiconOnlyElectron'))
    }
  }

  const chooseLexiconFile = async () => {
    if (!window.wmatrixDesktop?.openProjectFile) {
      setMsg(t(language as never, 'openLexiconOnlyElectron'))
      return
    }
    const res = await window.wmatrixDesktop.openProjectFile()
    if (res.canceled || !res.path) return
    setLexiconPath(res.path)
    await reloadBootstrap()
    setMsg(`${t(language as never, 'lexiconPathSelected')}: ${res.path}`)
  }

  const totalEntries = (overview?.domains ?? []).reduce((sum, d) => sum + (d.count || 0), 0)

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'lexiconTitle')}</Typography>
      {err ? <Alert severity="error">{err}</Alert> : null}

      {overview && (
        <Paper sx={{ p: 2 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} justifyContent="space-around">
            <Typography variant="body2"><b>{t(language as never, 'tableDomain')}:</b> {overview.domains.length}</Typography>
            <Typography variant="body2"><b>{t(language as never, 'tokensCount')}:</b> {totalEntries}</Typography>
            <Typography variant="body2" sx={{ wordBreak: 'break-all' }}><b>{t(language as never, 'lexiconPath')}:</b> {overview.path}</Typography>
          </Stack>
        </Paper>
      )}

      <Card>
        <CardHeader title={t(language as never, 'addLemmaTitle')} titleTypographyProps={{ variant: 'subtitle1' }} />
        <CardContent>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                label={t(language as never, 'domainCode')}
                value={domainCode}
                onChange={(e) => setDomainCode(e.target.value)}
                size="small"
                sx={{ minWidth: 180 }}
              />
              <TextField
                label={t(language as never, 'lemma')}
                value={lemma}
                onChange={(e) => setLemma(e.target.value)}
                size="small"
                sx={{ flex: 1 }}
              />
              <TextField
                label={t(language as never, 'moveToDomain')}
                value={moveToDomain}
                onChange={(e) => setMoveToDomain(e.target.value)}
                size="small"
                sx={{ minWidth: 180 }}
              />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button variant="contained" onClick={() => void addTerm()} disabled={!lemma.trim()}>
                {t(language as never, 'add')}
              </Button>
              <Button
                variant="outlined"
                onClick={() =>
                  showConfirm(
                    t(language as never, 'removeTerm'),
                    `${t(language as never, 'removeTermConfirm')}: ${lemma.trim()} (${domainCode})`,
                    () => void removeTerm(),
                  )
                }
                disabled={!lemma.trim()}
              >
                {t(language as never, 'removeTerm')}
              </Button>
              <Button variant="outlined" onClick={() => void moveTerm()} disabled={!lemma.trim() || !moveToDomain.trim()}>
                {t(language as never, 'moveTerm')}
              </Button>
              <Button
                variant="outlined"
                color="warning"
                onClick={() =>
                  showConfirm(
                    t(language as never, 'removeDomain'),
                    `${t(language as never, 'removeDomainConfirm')}: ${domainCode}`,
                    () => void removeDomain(),
                  )
                }
                disabled={!domainCode.trim()}
              >
                {t(language as never, 'removeDomain')}
              </Button>
            </Stack>
            <Divider />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button variant="outlined" onClick={() => void chooseLexiconFile()}>
                {t(language as never, 'chooseLexiconFile')}
              </Button>
              <Button variant="outlined" onClick={() => void saveLexiconAs()}>
                {t(language as never, 'saveLexiconSnapshot')}
              </Button>
              <Button variant="outlined" onClick={() => { setKeyword(lemma || ''); nav('/kwic') }}>
                {t(language as never, 'openKwic')}
              </Button>
            </Stack>
          </Stack>
          {msg ? <Alert sx={{ mt: 2 }} severity="info">{msg}</Alert> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader title={t(language as never, 'semanticTaggerImport')} titleTypographyProps={{ variant: 'subtitle1' }} />
        <CardContent>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button variant="outlined" onClick={() => void importAnalyzedLemmas(true)}>
                {t(language as never, 'importSelectedDomainLemmas')}
              </Button>
              <Button variant="outlined" onClick={() => void importAnalyzedLemmas(false)}>
                {t(language as never, 'importAllAnalyzedLemmas')}
              </Button>
            </Stack>
            <Typography variant="subtitle2">{t(language as never, 'batchImport')}</Typography>
            <TextField
              multiline
              minRows={5}
              label={t(language as never, 'batchImportHint')}
              value={bulkText}
              onChange={(e) => setBulkText(e.target.value)}
            />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <Button variant="outlined" onClick={() => void addBulk()} disabled={!bulkText.trim()}>
                {t(language as never, 'importPastedText')}
              </Button>
              <Button variant="outlined" onClick={() => fileInputRef.current?.click()}>
                {t(language as never, 'importFromFile')}
              </Button>
            </Stack>
            <input
              ref={fileInputRef}
              type="file"
              hidden
              accept=".txt,.csv,.json"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (!file) return
                void file.text().then((content) => addBulk(content))
                e.target.value = ''
              }}
            />
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="subtitle1">{t(language as never, 'overviewTitle')}</Typography>
      <Table size="small" component={Paper}>
        <TableHead>
          <TableRow>
            <TableCell>{t(language as never, 'tableDomain')}</TableCell>
            <TableCell>{t(language as never, 'tableLabel')}</TableCell>
            <TableCell align="right">{t(language as never, 'tableCount')}</TableCell>
            <TableCell>{t(language as never, 'tableSampleWords')}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(overview?.domains ?? []).map((d) => (
            <TableRow
              key={d.domain_code}
              hover
              sx={{ cursor: 'pointer' }}
              onClick={() => {
                setDomainCode(d.domain_code)
                setSelectedDomain(d.domain_code)
              }}
            >
              <TableCell>
                <Chip
                  size="small"
                  label={d.domain_code}
                  sx={{ bgcolor: getDomainColor(d.domain_code), color: '#fff', fontWeight: 600 }}
                />
              </TableCell>
              <TableCell>{d.domain_label}</TableCell>
              <TableCell align="right">{d.count}</TableCell>
              <TableCell sx={{ maxWidth: 480, whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                {d.words.slice(0, 12).join(', ') + (d.words.length > 12 ? ` ... +${d.words.length - 12} more` : '')}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>{confirmAction?.title}</DialogTitle>
        <DialogContent>
          <DialogContentText>{confirmAction?.text}</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>{t(language as never, 'close')}</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              confirmAction?.onConfirm()
              setConfirmOpen(false)
            }}
          >
            {t(language as never, 'confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
