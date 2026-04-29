import {
  Alert,
  Button,
  Box,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiPostJson } from '../api/client'
import { useWorkbench } from '../contexts/WorkbenchContext'
import { t } from '../i18n'
import type { KwicRow } from '../types/models'
import { useNavigate } from 'react-router-dom'

export function KwicPage(): JSX.Element {
  const nav = useNavigate()
  const { apiBase, result, selectedDomain, keyword, setKeyword, language } = useWorkbench()
  const [domainCode, setDomainCode] = useState('')
  const [posFilter, setPosFilter] = useState('')
  const [useRegex, setUseRegex] = useState(false)
  const [rows, setRows] = useState<KwicRow[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [openRow, setOpenRow] = useState<KwicRow | null>(null)
  const [infoMsg, setInfoMsg] = useState<string | null>(null)
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null)
  const [menuRow, setMenuRow] = useState<KwicRow | null>(null)

  useEffect(() => {
    setDomainCode((prev) => prev || selectedDomain || '')
  }, [selectedDomain])

  const effectiveDomain = useMemo(() => domainCode || selectedDomain || '', [domainCode, selectedDomain])

  const runKwic = useCallback(async () => {
    const k = keyword.trim()
    if (!k) {
      setErr(t(language as never, 'needKeyword'))
      setRows([])
      return
    }
    setLoading(true)
    setErr(null)
    setInfoMsg(null)
    try {
      const data = await apiPostJson<KwicRow[]>(apiBase, '/kwic', {
        keyword: k,
        domain_code: effectiveDomain,
        pos_filter: posFilter,
        use_regex: useRegex,
      })
      setRows(data)
      if (!data.length) {
        setInfoMsg(t(language as never, 'noRows'))
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [apiBase, effectiveDomain, keyword, language, posFilter, useRegex])

  const copyText = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value)
      setInfoMsg(t(language as never, 'copied'))
    } catch {
      const ta = document.createElement('textarea')
      ta.value = value
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setInfoMsg(t(language as never, 'copied'))
    }
  }

  const exportKwicCsv = async () => {
    if (!rows.length) {
      return
    }
    if (!window.wmatrixDesktop?.saveFile) {
      setErr(t(language as never, 'exportOnlyElectron'))
      return
    }
    const header = ['line,left,key,right,domain_code,source_offset,sentence_index,confidence'].join(',')
    const body = rows
      .map((r) => {
        const esc = (s: unknown) => `"${String(s ?? '').replace(/"/g, '""')}"`
        return [
          esc(r.line),
          esc(r.left),
          esc(r.key),
          esc(r.right),
          esc(r.domain_code),
          esc(r.source_offset),
          esc(r.sentence_index),
          esc(r.confidence),
        ].join(',')
      })
      .join('\n')
    const content = `${header}\n${body}\n`
    const suggested = `kwic-${keyword.trim() || t(language as never, 'kwicKeywordFallback')}.csv`
    const res = await window.wmatrixDesktop.saveFile(suggested, content)
    if (!res.canceled) {
      setInfoMsg(`${t(language as never, 'savedKwic')}: ${res.path || suggested}`)
    }
  }

  useEffect(() => {
    const handler = (evt: Event) => {
      const action = (evt as CustomEvent<string>).detail
      if (action === 'tools.kwic') {
        void runKwic()
      }
    }
    window.addEventListener('bunseki:menu-action', handler)
    return () => window.removeEventListener('bunseki:menu-action', handler)
  }, [runKwic])

  useEffect(() => {
    if (!result) {
      return
    }
    if (keyword.trim()) {
      void runKwic()
    }
  }, [keyword, effectiveDomain, result, runKwic])

  if (!result) {
    return (
      <Stack spacing={2}>
        <Typography variant="h5">{t(language as never, 'kwic')}</Typography>
        <Alert severity="info">{t(language as never, 'runAnalyzeFirst')}</Alert>
      </Stack>
    )
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'kwic')}</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField
          label={t(language as never, 'keywordLemma')}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              void runKwic()
            }
          }}
          size="small"
          sx={{ flex: 1 }}
        />
        <TextField
          label={t(language as never, 'domainFilter')}
          value={domainCode}
          onChange={(e) => setDomainCode(e.target.value)}
          placeholder={selectedDomain || t(language as never, 'any')}
          size="small"
          sx={{ width: 220 }}
        />
        <TextField
          label={t(language as never, 'kwicPosFilter')}
          value={posFilter}
          onChange={(e) => setPosFilter(e.target.value)}
          placeholder={t(language as never, 'kwicPosFilterHint')}
          size="small"
          sx={{ width: 220 }}
        />
        <FormControlLabel
          control={<Checkbox checked={useRegex} onChange={(e) => setUseRegex(e.target.checked)} />}
          label={t(language as never, 'kwicRegex')}
        />
        <Button variant="contained" onClick={() => void runKwic()} disabled={loading}>
          {loading ? t(language as never, 'searching') : t(language as never, 'search')}
        </Button>
        <Button variant="outlined" onClick={() => void exportKwicCsv()} disabled={!rows.length}>
          {t(language as never, 'exportKwicCsv')}
        </Button>
      </Stack>
      {err ? <Alert severity="error">{err}</Alert> : null}
      {infoMsg ? <Alert severity="info">{infoMsg}</Alert> : null}
      <Table size="small" component={Paper}>
        <TableHead>
          <TableRow>
            <TableCell>{t(language as never, 'kwicLine')}</TableCell>
            <TableCell>{t(language as never, 'kwicLeft')}</TableCell>
            <TableCell>{t(language as never, 'kwicKey')}</TableCell>
            <TableCell>{t(language as never, 'kwicRight')}</TableCell>
            <TableCell>{t(language as never, 'kwicSentence')}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r, i) => {
            const parts = (typeof r.current === 'string' ? r.current : `${r.left ?? ''}${r.key ?? ''}${r.right ?? ''}`).split(
              new RegExp(`(${String(r.key ?? '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
            )
            return (
              <Tooltip key={i} title={t(language as never, 'dblClickContext')} placement="top">
                <TableRow
                  hover
                  sx={{ cursor: 'pointer' }}
                  onDoubleClick={() => setOpenRow(r)}
                  onContextMenu={(e) => {
                    e.preventDefault()
                    setMenuAnchor(e.currentTarget)
                    setMenuRow(r)
                  }}
                >
                  <TableCell sx={{ color: 'text.secondary', fontSize: '0.8rem' }}>{String(r.line ?? '')}</TableCell>
                  <TableCell sx={{ whiteSpace: 'pre-wrap', maxWidth: 280, fontFamily: 'monospace', textAlign: 'right', fontSize: '0.85rem' }}>
                    {String(r.left ?? '')}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, textAlign: 'center', color: 'primary.main', fontSize: '0.9rem' }}>
                    {String(r.key ?? '')}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'pre-wrap', maxWidth: 280, fontFamily: 'monospace', textAlign: 'left', fontSize: '0.85rem' }}>
                    {String(r.right ?? '')}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'pre-wrap', maxWidth: 420 }}>
                    {parts.map((part, j) =>
                      part.toLowerCase() === String(r.key ?? '').toLowerCase()
                        ? <Box key={j} component="mark" sx={{ bgcolor: 'warning.light', px: 0.2, borderRadius: '2px' }}>{part}</Box>
                        : part,
                    )}
                  </TableCell>
                </TableRow>
              </Tooltip>
            )
          })}
        </TableBody>
      </Table>

      <Menu
        open={!!menuAnchor}
        anchorEl={menuAnchor}
        onClose={() => {
          setMenuAnchor(null)
          setMenuRow(null)
        }}
      >
        <MenuItem
          onClick={() => {
            const r = menuRow
            if (r) {
              const lemma = String(r.key ?? '').trim()
              const domain = String(r.domain_code ?? '').trim()
              nav(`/lexicon?lemma=${encodeURIComponent(lemma)}&domain=${encodeURIComponent(domain)}`)
            }
            setMenuAnchor(null)
            setMenuRow(null)
          }}
        >
          {t(language as never, 'addToLexicon')}
        </MenuItem>
        <MenuItem
          onClick={() => {
            const r = menuRow
            if (r) {
              void copyText(`${r.left ?? ''}${r.key ?? ''}${r.right ?? ''}`)
            }
            setMenuAnchor(null)
            setMenuRow(null)
          }}
        >
          {t(language as never, 'copyRow')}
        </MenuItem>
        <MenuItem
          onClick={() => {
            const r = menuRow
            if (r) {
              void copyText(String(r.key ?? ''))
            }
            setMenuAnchor(null)
            setMenuRow(null)
          }}
        >
          {t(language as never, 'copyKey')}
        </MenuItem>
        <MenuItem
          onClick={() => {
            const r = menuRow
            if (r) {
              void copyText(`${r.previous ?? ''}\n${r.current ?? ''}\n${r.next ?? ''}`)
            }
            setMenuAnchor(null)
            setMenuRow(null)
          }}
        >
          {t(language as never, 'copyContext')}
        </MenuItem>
      </Menu>

      <Dialog open={!!openRow} onClose={() => setOpenRow(null)} maxWidth="md" fullWidth>
        <DialogTitle>{t(language as never, 'contextDetail')}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1}>
            <Typography variant="body2" color="text.secondary">
              {t(language as never, 'domain')}: {String(openRow?.domain_code || '')} / {t(language as never, 'offset')}:{' '}
              {String(openRow?.source_offset ?? '')}
            </Typography>
            <Typography variant="subtitle2">{t(language as never, 'previous')}</Typography>
            <Typography sx={{ whiteSpace: 'pre-wrap' }}>{String(openRow?.previous || '')}</Typography>
            <Typography variant="subtitle2">{t(language as never, 'current')}</Typography>
            <Typography sx={{ whiteSpace: 'pre-wrap' }}>{String(openRow?.current || '')}</Typography>
            <Typography variant="subtitle2">{t(language as never, 'next')}</Typography>
            <Typography sx={{ whiteSpace: 'pre-wrap' }}>{String(openRow?.next || '')}</Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRow(null)}>{t(language as never, 'close')}</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
