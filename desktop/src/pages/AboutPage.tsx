import { Alert, Box, Chip, Divider, Link, Paper, Stack, Typography } from '@mui/material'
import { useWorkbench } from '../contexts/WorkbenchContext'
import { t } from '../i18n'

const APP_VERSION = '2.0.0'
const TECH_STACK = ['Python', 'FastAPI', 'SudachiPy', 'React', 'MUI', 'Plotly', 'D3', 'Electron']

export function AboutPage(): JSX.Element {
  const { apiBase, bootstrap, language } = useWorkbench()
  const about = bootstrap?.about
  const ccIcon = about?.cc_icon_url ? `${apiBase}${about.cc_icon_url}` : ''

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'aboutTitle')}</Typography>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1}>
          <Typography>
            <b>{t(language as never, 'aboutAuthor')}:</b> {about?.author || 'Zhang Wenze'}
          </Typography>
          <Typography>
            <b>{t(language as never, 'aboutOrganization')}:</b> {about?.organization || 'School of Foreign Languages, Xinjiang University'}
          </Typography>
          <Typography>
            <b>{t(language as never, 'aboutLicense')}:</b> {about?.license || 'CC-BY-NC-ND 4.0'}
          </Typography>
          {ccIcon ? (
            <Box sx={{ pt: 1 }}>
              <img src={ccIcon} alt={t(language as never, 'ccLicenseIconAlt')} style={{ width: 180, maxWidth: '100%' }} />
            </Box>
          ) : (
            <Alert severity="info">{t(language as never, 'ccIconUnavailable')}</Alert>
          )}
          <Link href="https://creativecommons.org/licenses/by-nc-nd/4.0/" target="_blank" rel="noreferrer">
            {t(language as never, 'ccLicenseDetails')}
          </Link>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1.5}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography sx={{ minWidth: 80 }}><b>{t(language as never, 'aboutVersion')}:</b></Typography>
            <Chip label={`v${APP_VERSION}`} color="primary" size="small" />
          </Stack>
          <Divider />
          <Stack spacing={1}>
            <Typography><b>{t(language as never, 'aboutTechStack')}:</b></Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
              {TECH_STACK.map((tech) => (
                <Chip key={tech} label={tech} variant="outlined" size="small" sx={{ mb: 0.5 }} />
              ))}
            </Stack>
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  )
}

