import {
  Alert,
  Box,
  Chip,
  InputAdornment,
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
import SearchIcon from '@mui/icons-material/Search'
import { useEffect, useMemo, useState } from 'react'
import { apiGetJson } from '../api/client'
import { DomainBarPlot } from '../components/charts/DomainBarPlot'
import { DomainNetworkD3 } from '../components/charts/DomainNetworkD3'
import { useWorkbench } from '../contexts/WorkbenchContext'
import { getDomainColor } from '../utils/domainColors'
import { useNavigate } from 'react-router-dom'
import { t } from '../i18n'

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Paper sx={{ p: 2, flex: 1, minWidth: 140, textAlign: 'center' }}>
      <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>{value}</Typography>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
    </Paper>
  )
}

export function ProfilePage(): JSX.Element {
  const nav = useNavigate()
  const { apiBase, result, profile, selectedDomain, setSelectedDomain, setKeyword, language } = useWorkbench()
  const [domainWords, setDomainWords] = useState<Array<Record<string, unknown>>>([])
  const [domainWordsErr, setDomainWordsErr] = useState<string | null>(null)
  const [domainFilter, setDomainFilter] = useState('')
  const domainFreq = (result?.domain_frequency as Record<string, number> | undefined) || {}
  const [profileRows, setProfileRows] = useState<Array<Record<string, unknown>>>(
    Array.isArray(profile) ? (profile as Array<Record<string, unknown>>) : [],
  )
  const safeTokens = useMemo(
    () => (Array.isArray(result?.tokens) ? result!.tokens.filter((x) => !!x && typeof x === 'object') : []),
    [result],
  )

  useEffect(() => {
    if (!result) {
      setProfileRows([])
      return
    }
    apiGetJson<{ ok: boolean; profile?: Array<Record<string, unknown>> }>(
      apiBase,
      `/domain-profile?language=${encodeURIComponent(language)}`,
    )
      .then((data) => {
        if (data.ok && Array.isArray(data.profile)) {
          setProfileRows(data.profile)
        }
      })
      .catch(() => {
        setProfileRows(Array.isArray(profile) ? (profile as Array<Record<string, unknown>>) : [])
      })
  }, [apiBase, language, profile, result])

  useEffect(() => {
    if (!selectedDomain) {
      setDomainWords([])
      return
    }
    setDomainWordsErr(null)
    apiGetJson<Array<Record<string, unknown>> | { ok?: boolean; data?: Array<Record<string, unknown>> }>(
      apiBase,
      `/domain-words/${encodeURIComponent(selectedDomain)}`,
    )
      .then((resp) => {
        if (Array.isArray(resp)) {
          setDomainWords(resp)
          return
        }
        if (resp && Array.isArray(resp.data)) {
          setDomainWords(resp.data)
          return
        }
        setDomainWords([])
      })
      .catch((e: unknown) => setDomainWordsErr(e instanceof Error ? e.message : String(e)))
  }, [apiBase, selectedDomain])

  const filteredRows = useMemo(() => {
    const q = domainFilter.trim().toLowerCase()
    if (!q) return profileRows
    return profileRows.filter(
      (r) =>
        String(r.domain_code || '').toLowerCase().includes(q) ||
        String(r.domain_label || r.label || '').toLowerCase().includes(q),
    )
  }, [profileRows, domainFilter])

  const maxPer10k = useMemo(
    () => Math.max(0, ...domainWords.slice(0, 200).map((r) => Number(r.relative_per_10k ?? 0))),
    [domainWords],
  )

  if (!result) {
    return (
      <Stack spacing={2}>
        <Typography variant="h5">{t(language as never, 'profileTitle')}</Typography>
        <Alert severity="info">{t(language as never, 'runAnalyzeFirst')}</Alert>
      </Stack>
    )
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'profileTitle')}</Typography>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <StatCard label={t(language as never, 'domainRows')} value={profileRows.length} />
        <StatCard
          label={t(language as never, 'domain')}
          value={selectedDomain || profileRows[0]?.domain_label ? String(profileRows[0]?.domain_label ?? '') : '-'}
        />
        <StatCard label={t(language as never, 'tokensCount')} value={String(result.summary?.token_count ?? '')} />
        <StatCard label={t(language as never, 'uniqueLemmas')} value={String(result.summary?.unique_lemma_count ?? '')} />
      </Stack>

      <Paper sx={{ p: 2 }}>
        <DomainBarPlot domainFrequency={domainFreq} title={t(language as never, 'profileDomainFreqTop')} />
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          {t(language as never, 'domainTransitionNetwork')}
        </Typography>
        <DomainNetworkD3
          tokens={safeTokens}
          emptyText={t(language as never, 'domainNetworkEmpty')}
          onNodeClick={(domainCode) => {
            setSelectedDomain(domainCode)
          }}
        />
      </Paper>

      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" spacing={1}>
        <Typography variant="subtitle1">{t(language as never, 'domainRows')}</Typography>
        <TextField
          size="small"
          placeholder={`${t(language as never, 'search')}...`}
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 220 }}
        />
      </Stack>

      <Table size="small" component={Paper}>
        <TableHead>
          <TableRow>
            <TableCell>{t(language as never, 'tableDomain')}</TableCell>
            <TableCell>{t(language as never, 'tableLabel')}</TableCell>
            <TableCell align="right">{t(language as never, 'tableCount')}</TableCell>
            <TableCell align="right">{t(language as never, 'frequency')}</TableCell>
            <TableCell align="right">{t(language as never, 'per10k')}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredRows.map((row) => (
            <TableRow
              key={String(row.domain_code || '')}
              hover
              selected={String(row.domain_code || '') === selectedDomain}
              onClick={() => setSelectedDomain(String(row.domain_code || ''))}
              sx={{ cursor: 'pointer' }}
            >
              <TableCell>
                <Chip
                  size="small"
                  label={String(row.domain_code || '')}
                  sx={{ bgcolor: getDomainColor(String(row.domain_code || '')), color: '#fff', fontWeight: 600 }}
                />
              </TableCell>
              <TableCell>{String(row.domain_label ?? row.label ?? '')}</TableCell>
              <TableCell align="right">{String(row.tokens ?? row.frequency ?? row.count ?? '')}</TableCell>
              <TableCell align="right">{String(row.frequency ?? row.count ?? '')}</TableCell>
              <TableCell align="right">{String(row.relative_per_10k ?? '')}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {selectedDomain && (
        <Chip
          label={`${t(language as never, 'selectedDomainForKwic')}: ${selectedDomain}`}
          color="primary"
          variant="outlined"
          onClick={() => { setKeyword(''); nav('/kwic') }}
          sx={{ alignSelf: 'flex-start', cursor: 'pointer' }}
        />
      )}

      <Typography variant="subtitle1">{t(language as never, 'domainWords')}</Typography>

      {domainWordsErr ? <Alert severity="error">{domainWordsErr}</Alert> : null}
      <Table size="small" component={Paper}>
        <TableHead>
          <TableRow>
            <TableCell>{t(language as never, 'word')}</TableCell>
            <TableCell>{t(language as never, 'lemma')}</TableCell>
            <TableCell align="right">{t(language as never, 'frequency')}</TableCell>
            <TableCell align="right" sx={{ minWidth: 140 }}>{t(language as never, 'per10k')}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {domainWords.slice(0, 200).map((row, i) => {
            const per10kVal = Number(row.relative_per_10k ?? 0)
            const barWidth = maxPer10k > 0 ? `${(per10kVal / maxPer10k) * 100}%` : '0%'
            return (
              <TableRow
                key={`${String(row.lemma || row.surface || '')}-${i}`}
                hover
                sx={{ cursor: 'pointer' }}
                onClick={() => {
                  setKeyword(String(row.lemma || row.surface || ''))
                  nav('/kwic')
                }}
              >
                <TableCell>{String(row.word || '')}</TableCell>
                <TableCell>{String(row.lemma || '')}</TableCell>
                <TableCell align="right">{String(row.frequency ?? '')}</TableCell>
                <TableCell align="right" sx={{ position: 'relative' }}>
                  <Box
                    sx={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: barWidth,
                      bgcolor: 'primary.light',
                      opacity: 0.15,
                      transition: 'width 0.3s',
                    }}
                  />
                  <span style={{ position: 'relative' }}>{String(row.relative_per_10k ?? '')}</span>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </Stack>
  )
}
