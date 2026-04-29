import { Box, Skeleton, Typography, useTheme } from '@mui/material'
import { Suspense, lazy, useMemo } from 'react'
import type { Data, Layout } from 'plotly.js'

const Plot = lazy(() => import('react-plotly.js'))

type Props = {
  domainFrequency: Record<string, number>
  title?: string
  maxBars?: number
  xTitle?: string
  yTitle?: string
  colorMap?: Record<string, string>
  emptyText?: string
}

export function DomainBarPlot({
  domainFrequency,
  title = 'Domain frequency',
  maxBars = 24,
  xTitle = 'Domain',
  yTitle = 'Count',
  colorMap,
  emptyText,
}: Props): JSX.Element {
  const theme = useTheme()

  const { data, layout } = useMemo(() => {
    const entries = Object.entries(domainFrequency)
      .filter(([, v]) => typeof v === 'number' && v > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, maxBars)
    const x = entries.map((e) => e[0])
    const y = entries.map((e) => e[1])
    const barColors = colorMap
      ? x.map((code) => colorMap[code] || theme.palette.primary.main)
      : theme.palette.primary.main

    const plotData: Data[] = [
      {
        type: 'bar',
        x,
        y,
        marker: { color: barColors },
      },
    ]
    const plotLayout: Partial<Layout> = {
      title: { text: title, font: { size: 14 } },
      margin: { t: 48, r: 16, b: 80, l: 48 },
      xaxis: { title: xTitle, tickangle: -45 },
      yaxis: { title: yTitle },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      autosize: true,
    }
    return { data: plotData, layout: plotLayout }
  }, [domainFrequency, maxBars, title, xTitle, yTitle, colorMap, theme.palette.primary.main])

  if (Object.keys(domainFrequency).length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyText || 'No domain counts to plot.'}
      </Typography>
    )
  }

  return (
    <Box sx={{ width: '100%', minHeight: 360 }}>
      <Suspense fallback={<Skeleton variant="rectangular" height={360} animation="wave" />}>
        <Plot
          data={data}
          layout={layout}
          config={{ displayModeBar: true, responsive: true }}
          style={{ width: '100%', height: 360 }}
          useResizeHandler
        />
      </Suspense>
    </Box>
  )
}
