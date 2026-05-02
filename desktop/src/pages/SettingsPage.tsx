import {
  Alert,
  Box,
  Button,
  Chip,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useState } from 'react'
import { t } from '../i18n'
import { useWorkbench } from '../contexts/WorkbenchContext'
import { apiGetJson, apiPostJson } from '../api/client'

type Constraints = Record<string, unknown>
type JsonVal = string | number | boolean | null | JsonVal[] | { [k: string]: JsonVal }

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return []
  return v.map((x) => String(x ?? '').trim()).filter(Boolean)
}

// ---- LLM config types -------------------------------------------------------
interface LlmConfig {
  provider: string
  fallback_chain: string[]
  api_keys: Record<string, string>
  local_model_path: string
  is_available: boolean
}

const LLM_PROVIDERS = [
  { value: 'none', labelKey: 'none' },
  { value: 'deepseek', labelKey: 'deepseek' },
  { value: 'openai', labelKey: 'openai' },
  { value: 'gemini', labelKey: 'gemini' },
  { value: 'claude', labelKey: 'claude' },
  { value: 'local', labelKey: 'local' },
]

const PROVIDER_LABEL_MAP: Record<string, string> = {
  none: 'None (deterministic only)',
  deepseek: 'DeepSeek',
  openai: 'OpenAI',
  gemini: 'Google Gemini',
  claude: 'Claude (Anthropic)',
  local: 'Local (llama-cpp)',
}

export function SettingsPage(): JSX.Element {
  const { language, apiBase } = useWorkbench()
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [okMsg, setOkMsg] = useState<string | null>(null)
  const [raw, setRaw] = useState<Constraints>({})

  // LLM config state
  const [llmProvider, setLlmProvider] = useState('none')
  const [llmChain, setLlmChain] = useState('deepseek, openai, gemini, claude')
  const [llmKeys, setLlmKeys] = useState<Record<string, string>>({})
  const [llmLocalPath, setLlmLocalPath] = useState('')
  const [llmAvailable, setLlmAvailable] = useState(false)
  const [llmLoading, setLlmLoading] = useState(false)

  const allowed = useMemo(() => asStringArray(raw.allowed_pos_prefixes), [raw])
  const blocked = useMemo(() => asStringArray(raw.blocked_pos_prefixes), [raw])
  const stopwords = useMemo(() => asStringArray(raw.stopwords), [raw])
  const mrwThreshold = Number(raw.mrw_distance_threshold ?? 0.25)
  const enableLayer3 = Boolean(raw.enable_mipvu_layer3)

  const load = async () => {
    if (!window.wmatrixDesktop?.getConstraints) {
      setErr(t(language as never, 'settingsOnlyElectron'))
      return
    }
    setLoading(true)
    setErr(null)
    setOkMsg(null)
    try {
      const res = await window.wmatrixDesktop.getConstraints()
      if (!res.ok) throw new Error(res.error || 'load_failed')
      setRaw((res.data as Constraints) || {})
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const loadLlmConfig = async () => {
    setLlmLoading(true)
    try {
      const data = await apiGetJson<{ ok: boolean } & LlmConfig>(
        apiBase,
        '/llm/config',
      )
      if (data.ok) {
        setLlmProvider(data.provider || 'none')
        setLlmChain((data.fallback_chain || []).join(', '))
        setLlmKeys(data.api_keys || {})
        setLlmLocalPath(data.local_model_path || '')
        setLlmAvailable(Boolean(data.is_available))
      }
    } catch {
      // LLM endpoints may not be available — ignore
    } finally {
      setLlmLoading(false)
    }
  }

  useEffect(() => {
    void load()
    void loadLlmConfig()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const save = async () => {
    if (!window.wmatrixDesktop?.setConstraints) {
      setErr(t(language as never, 'settingsOnlyElectron'))
      return
    }
    setLoading(true)
    setErr(null)
    setOkMsg(null)
    try {
      const res = await window.wmatrixDesktop.setConstraints(raw)
      if (!res.ok) throw new Error(res.error || 'save_failed')
      setOkMsg(t(language as never, 'saved'))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const saveLlmConfig = async () => {
    setLoading(true)
    setErr(null)
    setOkMsg(null)
    try {
      const chain = llmChain
        .split(/[,\n]/g)
        .map((s) => s.trim())
        .filter(Boolean)
      const data = await apiPostJson<{ ok: boolean; error?: string } & LlmConfig>(
        apiBase,
        '/llm/config',
        {
          provider: llmProvider,
          fallback_chain: chain,
          api_keys: llmKeys,
          local_model_path: llmLocalPath,
        },
      )
      if (!data.ok) throw new Error((data as { error?: string }).error || 'save_failed')
      // Refresh with masked keys returned from server
      setLlmKeys(data.api_keys || {})
      setLlmAvailable(Boolean(data.is_available))
      setOkMsg(t(language as never, 'llmConfigSaved'))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const setList = (key: string, text: string) => {
    const items = text
      .split(/[,\n]/g)
      .map((s) => s.trim())
      .filter(Boolean)
    setRaw((prev) => ({ ...prev, [key]: items }))
  }

  const handleKeyChange = (provider: string, value: string) => {
    setLlmKeys((prev) => ({ ...prev, [provider]: value }))
  }

  const apiKeyProviders = ['deepseek', 'openai', 'gemini', 'claude']

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'settingsTitle')}</Typography>
      <Alert severity="info" variant="outlined">
        {t(language as never, 'settingsHint')}
      </Alert>

      {err ? <Alert severity="error">{err}</Alert> : null}
      {okMsg ? <Alert severity="success">{okMsg}</Alert> : null}

      {/* ---- LLM / AI section ---- */}
      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="subtitle1">{t(language as never, 'llmSection')}</Typography>
          <Alert severity="info" variant="outlined" sx={{ fontSize: '0.85rem' }}>
            {t(language as never, 'llmConfigHint')}
          </Alert>

          <Box>
            <Alert severity={llmAvailable ? 'success' : 'warning'} variant="standard">
              {llmAvailable
                ? t(language as never, 'llmAvailable')
                : t(language as never, 'llmUnavailable')}
            </Alert>
          </Box>

          {/* Provider selector */}
          <Box>
            <InputLabel sx={{ mb: 0.5 }}>{t(language as never, 'llmProvider')}</InputLabel>
            <Select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
              fullWidth
              size="small"
              disabled={loading || llmLoading}
            >
              {LLM_PROVIDERS.map((p) => (
                <MenuItem key={p.value} value={p.value}>
                  {PROVIDER_LABEL_MAP[p.value] ?? p.value}
                </MenuItem>
              ))}
            </Select>
          </Box>

          {/* API key inputs */}
          {llmProvider !== 'none' && llmProvider !== 'local' && (
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {t(language as never, 'llmApiKey')}
              </Typography>
              <Stack spacing={1.5}>
                {apiKeyProviders.map((p) => (
                  <TextField
                    key={p}
                    label={PROVIDER_LABEL_MAP[p] ?? p}
                    value={llmKeys[p] || ''}
                    onChange={(e) => handleKeyChange(p, e.target.value)}
                    type="password"
                    size="small"
                    fullWidth
                    disabled={loading || llmLoading}
                    placeholder={p === llmProvider ? 'sk-...' : '(optional fallback)'}
                  />
                ))}
              </Stack>
            </Box>
          )}

          {/* Local model path */}
          {llmProvider === 'local' && (
            <TextField
              label={t(language as never, 'llmLocalModelPath')}
              value={llmLocalPath}
              onChange={(e) => setLlmLocalPath(e.target.value)}
              size="small"
              fullWidth
              disabled={loading || llmLoading}
              placeholder="./models/qwen3-4b-q4_k_m.gguf"
            />
          )}

          {/* Fallback chain */}
          <TextField
            label={t(language as never, 'llmFallbackChain')}
            value={llmChain}
            onChange={(e) => setLlmChain(e.target.value)}
            helperText={t(language as never, 'commaSeparated')}
            size="small"
            fullWidth
            disabled={loading || llmLoading}
          />

          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={() => void saveLlmConfig()} disabled={loading || llmLoading}>
              {t(language as never, 'save')}
            </Button>
            <Button variant="outlined" onClick={() => void loadLlmConfig()} disabled={loading || llmLoading}>
              {t(language as never, 'reload')}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* ---- MIPVU section ---- */}
      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="subtitle1">{t(language as never, 'mipvuSection')}</Typography>

          <FormControlLabel
            control={
              <Switch
                checked={enableLayer3}
                onChange={(e) => setRaw((p) => ({ ...p, enable_mipvu_layer3: e.target.checked }))}
              />
            }
            label={t(language as never, 'enableMipvuLayer3')}
          />

          <Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {t(language as never, 'mrwThreshold')}: <b>{Number.isFinite(mrwThreshold) ? mrwThreshold.toFixed(3) : '0.250'}</b>
            </Typography>
            <Slider
              min={0}
              max={1}
              step={0.01}
              value={Number.isFinite(mrwThreshold) ? mrwThreshold : 0.25}
              valueLabelDisplay="auto"
              onChange={(_, v) => setRaw((p) => ({ ...p, mrw_distance_threshold: Number(v) }))}
              disabled={loading}
            />
          </Box>
        </Stack>
      </Paper>

      {/* ---- Token filter section ---- */}
      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="subtitle1">{t(language as never, 'filterSection')}</Typography>
          <TextField
            label={t(language as never, 'allowedPos')}
            value={allowed.join(', ')}
            onChange={(e) => setList('allowed_pos_prefixes', e.target.value)}
            helperText={t(language as never, 'commaSeparated')}
            fullWidth
            size="small"
            disabled={loading}
          />
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            {allowed.map((p) => (
              <Chip key={p} size="small" label={p} />
            ))}
          </Stack>

          <TextField
            label={t(language as never, 'blockedPos')}
            value={blocked.join(', ')}
            onChange={(e) => setList('blocked_pos_prefixes', e.target.value)}
            helperText={t(language as never, 'commaSeparated')}
            fullWidth
            size="small"
            disabled={loading}
          />
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            {blocked.map((p) => (
              <Chip key={p} size="small" color="warning" label={p} />
            ))}
          </Stack>

          <TextField
            label={t(language as never, 'stopwords')}
            value={stopwords.join(', ')}
            onChange={(e) => setList('stopwords', e.target.value)}
            helperText={t(language as never, 'commaSeparated')}
            fullWidth
            size="small"
            disabled={loading}
          />
        </Stack>
      </Paper>

      <Stack direction="row" spacing={1}>
        <Button variant="contained" onClick={() => void save()} disabled={loading}>
          {t(language as never, 'save')}
        </Button>
        <Button variant="outlined" onClick={() => void load()} disabled={loading}>
          {t(language as never, 'reload')}
        </Button>
      </Stack>
    </Stack>
  )
}
