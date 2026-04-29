import { Alert, Box, Button, FormControl, InputLabel, MenuItem, Paper, Select, Skeleton, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, useTheme } from '@mui/material'
import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import type { Data, Layout } from 'plotly.js'
import { useWorkbench } from '../contexts/WorkbenchContext'
import { t } from '../i18n'
import { useNavigate } from 'react-router-dom'
import { apiPostJson } from '../api/client'

const Plot = lazy(() => import('react-plotly.js')) as unknown as React.ComponentType<any>

type Row = { term: string; count: number }

export function WordFrequencyPage(): JSX.Element {
  const nav = useNavigate()
  const theme = useTheme()
  const { apiBase, result, language, setKeyword } = useWorkbench()
  const [form, setForm] = useState<'lemma' | 'surface'>('lemma')
  const [posFilter, setPosFilter] = useState('')
  const [topN, setTopN] = useState(30)
  const [infoMsg, setInfoMsg] = useState<string | null>(null)
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)

  const posOptions = useMemo(() => {
    if (!result) {
      return []
    }
    const set = new Set<string>()
    for (const tok of result.tokens || []) {
      const pos = String(tok.pos || '').trim()
      if (pos) {
        set.add(pos)
      }
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b))
  }, [result])

  useEffect(() => {
    if (!result) {
      setRows([])
      return
    }
    setLoading(true)
    setInfoMsg(null)
    apiPostJson<{ ok: boolean; rows?: Row[]; error?: { message?: string } }>(apiBase, '/word-frequency', {
      form,
      pos_filter: posFilter,
      top_n: topN,
    })
      .then((data) => {
        if (!data.ok) {
          setInfoMsg(data.error?.message || t(language as never, 'wordFreqEmpty'))
          setRows([])
          return
        }
        setRows(Array.isArray(data.rows) ? data.rows : [])
      })
      .catch((e: unknown) => {
        setInfoMsg(e instanceof Error ? e.message : String(e))
        setRows([])
      })
      .finally(() => setLoading(false))
  }, [apiBase, form, language, posFilter, result, topN])

  const maxCount = useMemo(() => Math.max(0, ...rows.map((r) => r.count)), [rows])

  const chart = useMemo(() => {
    const x = rows.map((r) => r.term)
    const y = rows.map((r) => r.count)
    const data: Data[] = [{ type: 'bar', x, y, marker: { color: theme.palette.primary.main } }]
    const layout: Partial<Layout> = {
      title: { text: t(language as never, 'wordFreqChartTitle'), font: { size: 14 } },
      margin: { t: 48, r: 16, b: 120, l: 56 },
      xaxis: { title: t(language as never, 'wordFreqTermAxis'), tickangle: -45 },
      yaxis: { title: t(language as never, 'wordFreqCountAxis') },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      autosize: true,
    }
    return { data, layout }
  }, [language, rows, theme.palette.primary.main])

  const exportCsv = async () => {
    if (!rows.length) {
      return
    }
    if (!window.wmatrixDesktop?.saveFile) {
      setInfoMsg(t(language as never, 'exportOnlyElectron'))
      return
    }
    const header = ['term,count'].join(',')
    const body = rows
      .map((r) => {
        const esc = (s: unknown) => `"${String(s ?? '').replace(/"/g, '""')}"`
        return [esc(r.term), String(r.count)].join(',')
      })
      .join('\n')
    const content = `${header}\n${body}\n`
    const suggested = `word-frequency-${form}.csv`
    const res = await window.wmatrixDesktop.saveFile(suggested, content)
    if (!res.canceled) {
      setInfoMsg(`${t(language as never, 'saved')}: ${res.path || suggested}`)
    }
  }

  if (!result) {
    return (
      <Stack spacing={2}>
        <Typography variant="h5">{t(language as never, 'wordFrequency')}</Typography>
        <Alert severity="info">{t(language as never, 'runAnalyzeFirst')}</Alert>
      </Stack>
    )
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'wordFrequency')}</Typography>
      {infoMsg ? <Alert severity="info">{infoMsg}</Alert> : null}
      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>{t(language as never, 'wordFreqForm')}</InputLabel>
            <Select
              value={form}
              label={t(language as never, 'wordFreqForm')}
              onChange={(e) => setForm(String(e.target.value) as 'lemma' | 'surface')}
            >
              <MenuItem value="lemma">{t(language as never, 'wordFreqLemma')}</MenuItem>
              <MenuItem value="surface">{t(language as never, 'wordFreqSurface')}</MenuItem>
            </Select>
          </FormControl>
          <TextField
            size="small"
            label={t(language as never, 'wordFreqPosFilter')}
            value={posFilter}
            onChange={(e) => setPosFilter(e.target.value)}
            placeholder={posOptions.slice(0, 4).join(', ')}
            sx={{ minWidth: 360 }}
          />
          <TextField
            size="small"
            type="number"
            label={t(language as never, 'topN')}
            value={topN}
            onChange={(e) => setTopN(Math.max(1, Number(e.target.value) || 1))}
            sx={{ width: 140 }}
          />
          <Button variant="outlined" onClick={() => void exportCsv()} disabled={!rows.length}>
            {t(language as never, 'exportCsv')}
          </Button>
        </Stack>
      </Paper>
      <Paper sx={{ p: 2 }}>
        {rows.length ? (
          <Suspense fallback={<Skeleton variant="rectangular" height={380} animation="wave" />}>
            <Plot
              data={chart.data}
              layout={chart.layout}
              config={{ displayModeBar: true, responsive: true }}
              style={{ width: '100%', height: 380 }}
              useResizeHandler
              onClick={(evt: any) => {
                const term = String(evt?.points?.[0]?.x ?? '').trim()
                if (!term) return
                setKeyword(term)
                nav('/kwic')
              }}
            />
          </Suspense>
        ) : loading ? (
          <Alert severity="info">{t(language as never, 'searching')}</Alert>
        ) : (
          <Alert severity="info">{t(language as never, 'wordFreqEmpty')}</Alert>
        )}
      </Paper>
      <Table size="small" component={Paper}>
        <TableHead>
          <TableRow>
            <TableCell>{t(language as never, 'wordFreqTerm')}</TableCell>
            <TableCell align="right">{t(language as never, 'tableCount')}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => {
            const barWidth = maxCount > 0 ? `${(r.count / maxCount) * 100}%` : '0%'
            return (
              <TableRow
                key={r.term}
                hover
                sx={{ cursor: 'pointer' }}
                onClick={() => {
                  setKeyword(r.term)
                  nav('/kwic')
                }}
              >
                <TableCell>{r.term}</TableCell>
                <TableCell align="right" sx={{ position: 'relative' }}>
                  <Box
                    sx={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: barWidth,
                      bgcolor: 'primary.light',
                      opacity: 0.12,
                      transition: 'width 0.3s',
                    }}
                  />
                  <span style={{ position: 'relative' }}>{r.count}</span>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </Stack>
  )
}
