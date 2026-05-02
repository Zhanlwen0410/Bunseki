import MenuBookIcon from '@mui/icons-material/MenuBook'
import SettingsIcon from '@mui/icons-material/Settings'
import HubIcon from '@mui/icons-material/Hub'
import CompareArrowsIcon from '@mui/icons-material/CompareArrows'
import DashboardIcon from '@mui/icons-material/Dashboard'
import ViewListIcon from '@mui/icons-material/ViewList'
import BarChartIcon from '@mui/icons-material/BarChart'
import InfoIcon from '@mui/icons-material/Info'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import TranslateIcon from '@mui/icons-material/Translate'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import {
  Box,
  CssBaseline,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  LinearProgress,
  List,
  ListSubheader,
  MenuItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Select,
  Stack,
  Typography,
} from '@mui/material'
import { ThemeProvider } from '@mui/material/styles'
import { useEffect, useState } from 'react'
import { Link as RouterLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { WorkbenchProvider } from './contexts/WorkbenchContext'
import { theme } from './theme'
import { t } from './i18n'
import { ComparePage } from './pages/ComparePage'
import { KwicPage } from './pages/KwicPage'
import { LexiconPage } from './pages/LexiconPage'
import { ProfilePage } from './pages/ProfilePage'
import { WorkspacePage } from './pages/WorkspacePage'
import { AboutPage } from './pages/AboutPage'
import { HelpPage } from './pages/HelpPage'
import { WordFrequencyPage } from './pages/WordFrequencyPage'
import { SettingsPage } from './pages/SettingsPage'
import { useWorkbench } from './contexts/WorkbenchContext'
import { ErrorBoundary } from './components/common/ErrorBoundary'

const drawerWidth = 240
const drawerWidthCollapsed = 64

function Shell(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  const { language, setLanguage } = useWorkbench()
  const [collapsed, setCollapsed] = useState(false)
  const nav = [
    { to: '/workspace', label: t(language as never, 'workspace'), icon: <DashboardIcon /> },
    { to: '/profile', label: t(language as never, 'profile'), icon: <HubIcon /> },
    { to: '/kwic', label: t(language as never, 'kwic'), icon: <ViewListIcon /> },
    { to: '/word-frequency', label: t(language as never, 'wordFrequency'), icon: <BarChartIcon /> },
    { to: '/lexicon', label: t(language as never, 'lexicon'), icon: <MenuBookIcon /> },
    { to: '/compare', label: t(language as never, 'compare'), icon: <CompareArrowsIcon /> },
    { to: '/settings', label: t(language as never, 'settings'), icon: <SettingsIcon /> },
    { to: '/about', label: t(language as never, 'about'), icon: <InfoIcon /> },
    { to: '/help', label: t(language as never, 'help'), icon: <HelpOutlineIcon /> },
  ]

  useEffect(() => {
    if (!window.wmatrixDesktop?.onMenuAction) {
      return
    }
    const off = window.wmatrixDesktop.onMenuAction((action) => {
      const map: Record<string, string> = {
        'view.workspace': '/workspace',
        'view.profile': '/profile',
        'view.kwic': '/kwic',
        'view.lexicon': '/lexicon',
        'view.wordFrequency': '/word-frequency',
        'view.compare': '/compare',
        'help.about': '/about',
        'help.help': '/help',
      }
      if (map[action]) {
        navigate(map[action])
        return
      }
      if (
        action === 'file.openText' ||
        action === 'file.openProject' ||
        action === 'file.saveProject' ||
        action === 'file.exportCsv' ||
        action === 'file.exportJson' ||
        action === 'file.exportBundle' ||
        action === 'tools.analyze'
      ) {
        navigate('/workspace')
        setTimeout(() => window.dispatchEvent(new CustomEvent('bunseki:menu-action', { detail: action })), 0)
        return
      }
      window.dispatchEvent(new CustomEvent('bunseki:menu-action', { detail: action }))
    })
    return off
  }, [navigate])

  useEffect(() => {
    if (!window.wmatrixDesktop?.setMenuLanguage) {
      return
    }
    void window.wmatrixDesktop.setMenuLanguage(language)
  }, [language])

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: collapsed ? drawerWidthCollapsed : drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: collapsed ? drawerWidthCollapsed : drawerWidth,
            boxSizing: 'border-box',
            overflow: 'hidden',
          },
        }}
      >
        <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
          {!collapsed ? (
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <TranslateIcon color="primary" fontSize="small" />
                <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: '-0.01em', color: 'primary.main' }}>
                  Bunseki
                </Typography>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 3.5 }} noWrap>
                {t(language as never, 'appTagline')}
              </Typography>
            </Box>
          ) : null}
          <IconButton
            size="small"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? t(language as never, 'sidebarExpand') : t(language as never, 'sidebarCollapse')}
          >
            {collapsed ? <ChevronRightIcon fontSize="small" /> : <ChevronLeftIcon fontSize="small" />}
          </IconButton>
        </Box>
        <Box sx={{ px: 1.5, pb: 1.5 }}>
          <FormControl size="small" fullWidth>
            <Select
              value={language}
              onChange={(e) => setLanguage(String(e.target.value))}
              displayEmpty
              inputProps={{ 'aria-label': t(language as never, 'uiLanguage') }}
              sx={{
                ...(collapsed ? { '& .MuiSelect-select': { px: 1 } } : {}),
              }}
            >
              <MenuItem value="zh">中文</MenuItem>
              <MenuItem value="ja">日本語</MenuItem>
              <MenuItem value="en">English</MenuItem>
            </Select>
          </FormControl>
        </Box>
        <Divider />
        <List sx={{ overflow: 'auto' }} subheader={collapsed ? undefined : <li />}>
          {!collapsed && <ListSubheader sx={{ fontSize: '0.7rem', letterSpacing: '0.08em' }}>{t(language as never, 'menuAnalysis')}</ListSubheader>}
          {nav.slice(0, 6).map((item) => (
            <ListItemButton
              key={item.to}
              component={RouterLink}
              to={item.to}
              selected={location.pathname === item.to}
              sx={{ px: collapsed ? 1 : 2, mx: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: collapsed ? 40 : 56 }}>{item.icon}</ListItemIcon>
              {!collapsed ? <ListItemText primary={item.label} /> : null}
            </ListItemButton>
          ))}
        </List>
        <Divider />
        <List sx={{ overflow: 'auto' }}>
          {!collapsed && <ListSubheader sx={{ fontSize: '0.7rem', letterSpacing: '0.08em' }}>{t(language as never, 'menuInfo')}</ListSubheader>}
          {nav.slice(6).map((item) => (
            <ListItemButton
              key={item.to}
              component={RouterLink}
              to={item.to}
              selected={location.pathname === item.to}
              sx={{ px: collapsed ? 1 : 2, mx: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: collapsed ? 40 : 56 }}>{item.icon}</ListItemIcon>
              {!collapsed ? <ListItemText primary={item.label} /> : null}
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { sm: `calc(100% - ${(collapsed ? drawerWidthCollapsed : drawerWidth)}px)` },
          height: '100vh',
          overflow: 'auto',
          p: { xs: 2, md: 3 },
          maxWidth: 1400,
        }}
      >
        <Routes>
          <Route path="/" element={<Navigate to="/workspace" replace />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/kwic" element={<KwicPage />} />
          <Route path="/lexicon" element={<LexiconPage />} />
          <Route path="/word-frequency" element={<WordFrequencyPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/help" element={<HelpPage />} />
        </Routes>
      </Box>
    </Box>
  )
}

export default function App(): JSX.Element {
  const [apiBase, setApiBase] = useState<string | null>(null)
  const [bootErr, setBootErr] = useState<string | null>(null)

  useEffect(() => {
    const w = window as Window & { wmatrixDesktop?: { getApiBase: () => Promise<string> } }
    if (!w.wmatrixDesktop) {
      setBootErr(t('en', 'appBootError'))
      return
    }
    w.wmatrixDesktop
      .getApiBase()
      .then(setApiBase)
      .catch((e: unknown) => setBootErr(e instanceof Error ? e.message : String(e)))
  }, [])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {bootErr ? (
        <Box sx={{ p: 4 }}>
          <Typography color="error">{bootErr}</Typography>
        </Box>
      ) : !apiBase ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 2 }}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <TranslateIcon color="primary" fontSize="large" />
            <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>Bunseki</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary">Japanese Semantic Domain Analyzer</Typography>
          <Box sx={{ mt: 3, width: 240 }}>
            <LinearProgress />
          </Box>
        </Box>
      ) : (
        <WorkbenchProvider apiBase={apiBase}>
          <ErrorBoundary fallback={<Box sx={{ p: 4 }}><Typography color="error">Page crashed. Please return to Workspace and retry.</Typography></Box>}>
            <Shell />
          </ErrorBoundary>
        </WorkbenchProvider>
      )}
    </ThemeProvider>
  )
}
