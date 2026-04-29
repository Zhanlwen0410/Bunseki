import {
  Alert,
  Button,
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
import { useEffect, useMemo, useState } from 'react'
import { apiPostJson } from '../api/client'
import { DomainBarPlot } from '../components/charts/DomainBarPlot'
import { useWorkbench } from '../contexts/WorkbenchContext'
import type { ComparisonPayload } from '../types/models'
import { t } from '../i18n'

type CompareResponse = { ok: true; comparison: ComparisonPayload } | { ok: false; error: { message: string } }

export function ComparePage(): JSX.Element {
  const {
    apiBase,
    language,
    mode,
    minFrequency,
    topN,
    lexiconPath,
    text,
    result,
    compareLeft,
    setCompareLeft,
    compareRight,
    setCompareRight,
  } =
    useWorkbench()
  const [left, setLeft] = useState(compareLeft)
  const [right, setRight] = useState(compareRight)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [comparison, setComparison] = useState<ComparisonPayload | null>(null)

  useEffect(() => {
    if (result?.source_text && !left.trim()) {
      setLeft(String(result.source_text))
      setCompareLeft(String(result.source_text))
    }
  }, [left, result?.source_text, setCompareLeft])

  const run = async () => {
    setLoading(true)
    setErr(null)
    try {
      const data = await apiPostJson<CompareResponse>(apiBase, '/compare', {
        left_text: left,
        right_text: right,
        language,
        mode,
        min_frequency: minFrequency,
        top_n: topN.trim() === '' ? null : Number(topN),
        lexicon_path: lexiconPath || undefined,
      })
      if (!data.ok) {
        setErr(data.error.message)
        setComparison(null)
        return
      }
      setComparison(data.comparison)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setComparison(null)
    } finally {
      setLoading(false)
    }
  }

  const leftDomainFreq = useMemo(() => {
    if (!comparison) {
      return {}
    }
    const o: Record<string, number> = {}
    for (const row of comparison.domain_comparison) {
      o[row.key] = row.left_count
    }
    return o
  }, [comparison])

  const rightDomainFreq = useMemo(() => {
    if (!comparison) {
      return {}
    }
    const o: Record<string, number> = {}
    for (const row of comparison.domain_comparison) {
      o[row.key] = row.right_count
    }
    return o
  }, [comparison])

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'compareTitle')}</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
        <Button variant="outlined" onClick={() => { setLeft(text); setCompareLeft(text) }}>
          {t(language as never, 'useWorkspaceLeft')}
        </Button>
        <Button variant="outlined" onClick={() => { setRight(text); setCompareRight(text) }}>
          {t(language as never, 'useWorkspaceRight')}
        </Button>
      </Stack>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
        <TextField
          label={`${t(language as never, 'leftText')} (${left.length} ${t(language as never, 'chars')})`}
          value={left}
          onChange={(e) => {
            setLeft(e.target.value)
            setCompareLeft(e.target.value)
          }}
          multiline
          minRows={8}
          fullWidth
        />
        <TextField
          label={`${t(language as never, 'rightText')} (${right.length} ${t(language as never, 'chars')})`}
          value={right}
          onChange={(e) => {
            setRight(e.target.value)
            setCompareRight(e.target.value)
          }}
          multiline
          minRows={8}
          fullWidth
        />
      </Stack>
      <Button variant="contained" onClick={() => void run()} disabled={loading}>
        {loading ? t(language as never, 'comparing') : t(language as never, 'compareTitle')}
      </Button>
      {err ? <Alert severity="error">{err}</Alert> : null}
      {comparison ? (
        <>
          <Typography variant="subtitle1">{t(language as never, 'summary')}</Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Paper sx={{ p: 2, flex: 1, textAlign: 'center' }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>{comparison.summary.left_token_count}</Typography>
              <Typography variant="caption" color="text.secondary">{t(language as never, 'tokensCount')} ({t(language as never, 'left')})</Typography>
            </Paper>
            <Paper sx={{ p: 2, flex: 1, textAlign: 'center' }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'secondary.main' }}>{comparison.summary.right_token_count}</Typography>
              <Typography variant="caption" color="text.secondary">{t(language as never, 'tokensCount')} ({t(language as never, 'right')})</Typography>
            </Paper>
          </Stack>
          <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2}>
            <Paper sx={{ p: 2, flex: 1 }}>
              <DomainBarPlot domainFrequency={leftDomainFreq} title={t(language as never, 'compareLeftDomainCounts')} />
            </Paper>
            <Paper sx={{ p: 2, flex: 1 }}>
              <DomainBarPlot domainFrequency={rightDomainFreq} title={t(language as never, 'compareRightDomainCounts')} />
            </Paper>
          </Stack>
          <Typography variant="subtitle1">{t(language as never, 'domainDeltasTop')}</Typography>
          <Table size="small" component={Paper}>
            <TableHead>
              <TableRow>
                <TableCell>{t(language as never, 'domain')}</TableCell>
                <TableCell align="right">{t(language as never, 'left')}</TableCell>
                <TableCell align="right">{t(language as never, 'right')}</TableCell>
                <TableCell align="right">{t(language as never, 'delta')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {comparison.domain_comparison.slice(0, 40).map((r) => {
                const delta = Number(r.delta) || 0
                const deltaColor = delta > 0 ? 'success.main' : delta < 0 ? 'error.main' : 'text.secondary'
                return (
                  <TableRow key={r.key}>
                    <TableCell>{r.key}</TableCell>
                    <TableCell align="right">{r.left_count}</TableCell>
                    <TableCell align="right">{r.right_count}</TableCell>
                    <TableCell align="right">
                      <Typography component="span" sx={{ color: deltaColor, fontWeight: delta !== 0 ? 600 : 400 }}>
                        {delta > 0 ? '+' : ''}{r.delta}
                      </Typography>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          <Typography variant="subtitle1">{t(language as never, 'lemmaDeltasTop')}</Typography>
          <Table size="small" component={Paper}>
            <TableHead>
              <TableRow>
                <TableCell>{t(language as never, 'lemma')}</TableCell>
                <TableCell align="right">{t(language as never, 'left')}</TableCell>
                <TableCell align="right">{t(language as never, 'right')}</TableCell>
                <TableCell align="right">{t(language as never, 'delta')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {comparison.lemma_comparison.slice(0, 40).map((r) => {
                const delta = Number(r.delta) || 0
                const deltaColor = delta > 0 ? 'success.main' : delta < 0 ? 'error.main' : 'text.secondary'
                return (
                  <TableRow key={r.key}>
                    <TableCell>{r.key}</TableCell>
                    <TableCell align="right">{r.left_count}</TableCell>
                    <TableCell align="right">{r.right_count}</TableCell>
                    <TableCell align="right">
                      <Typography component="span" sx={{ color: deltaColor, fontWeight: delta !== 0 ? 600 : 400 }}>
                        {delta > 0 ? '+' : ''}{r.delta}
                      </Typography>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </>
      ) : null}
    </Stack>
  )
}
