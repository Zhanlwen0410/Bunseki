import { Accordion, AccordionDetails, AccordionSummary, Alert, Paper, Stack, Typography } from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { useWorkbench } from '../contexts/WorkbenchContext'
import { t } from '../i18n'

const HELP_SECTIONS = [
  { titleKey: 'helpGettingStartedTitle', contentKey: 'helpGettingStartedContent' },
  { titleKey: 'helpUnderstandingTitle', contentKey: 'helpUnderstandingContent' },
  { titleKey: 'helpProfileTitle', contentKey: 'helpProfileContent' },
  { titleKey: 'helpKwicTitle', contentKey: 'helpKwicContent' },
  { titleKey: 'helpLexiconTitle', contentKey: 'helpLexiconContent' },
  { titleKey: 'helpCompareTitle', contentKey: 'helpCompareContent' },
  { titleKey: 'helpProjectTitle', contentKey: 'helpProjectContent' },
]

export function HelpPage(): JSX.Element {
  const { bootstrap, language } = useWorkbench()
  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(language as never, 'helpTitle')}</Typography>

      {bootstrap?.help ? (
        <Paper sx={{ p: 2 }}>
          <Typography sx={{ whiteSpace: 'pre-wrap' }}>{bootstrap.help}</Typography>
        </Paper>
      ) : null}

      {HELP_SECTIONS.map(({ titleKey, contentKey }) => (
        <Accordion key={titleKey} defaultExpanded={false}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">{t(language as never, titleKey)}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
              {t(language as never, contentKey)}
            </Typography>
          </AccordionDetails>
        </Accordion>
      ))}

      <Alert severity="info">
        {t(language as never, 'legacyParityNote')}
      </Alert>
    </Stack>
  )
}

