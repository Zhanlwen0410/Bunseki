import { Box, Typography } from '@mui/material'
import * as d3 from 'd3'
import { useEffect, useRef, useState } from 'react'
import type { TokenRow } from '../../types/models'

type SimNode = d3.SimulationNodeDatum & { id: string; count: number }
type SimLink = d3.SimulationLinkDatum<SimNode> & { source: string | SimNode; target: string | SimNode; value?: number }

type Props = {
  tokens: TokenRow[]
  width?: number
  height?: number
  maxNodes?: number
  onNodeClick?: (domainCode: string) => void
  emptyText?: string
  colorMap?: Record<string, string>
}

/** Lightweight domain transition graph from consecutive token domain codes. */
export function DomainNetworkD3({
  tokens,
  width: initialWidth = 640,
  height: initialHeight = 420,
  maxNodes = 28,
  onNodeClick,
  emptyText,
  colorMap,
}: Props): JSX.Element {
  const ref = useRef<SVGSVGElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [svgSize, setSvgSize] = useState({ width: initialWidth, height: initialHeight })

  const safeTokens = Array.isArray(tokens)
    ? tokens.filter((tok): tok is TokenRow => Boolean(tok) && typeof tok === 'object')
    : []

  // Responsive resize
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w } = entry.contentRect
        if (w > 0) {
          setSvgSize({ width: w, height: Math.max(320, Math.round(w * 0.6)) })
        }
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const svgEl = ref.current
    if (!svgEl || !safeTokens.length) return

    const codes = safeTokens
      .map((t) => String(t.domain_code || '').trim())
      .filter((c) => c.length > 0)

    const freq = d3.rollup(codes, (v) => v.length, (d) => d)
    const top = [...freq.entries()].sort((a, b) => b[1] - a[1]).slice(0, maxNodes)
    const topSet = new Set(top.map((d) => d[0]))

    const linkMap = new Map<string, number>()
    for (let i = 1; i < codes.length; i += 1) {
      const a = codes[i - 1]
      const b = codes[i]
      if (!topSet.has(a) || !topSet.has(b) || a === b) continue
      const key = a < b ? `${a}|${b}` : `${b}|${a}`
      linkMap.set(key, (linkMap.get(key) || 0) + 1)
    }

    const nodes: SimNode[] = top.map(([id, count]) => ({ id, count }))
    const links: SimLink[] = [...linkMap.entries()].map(([key, value]) => {
      const [s, t] = key.split('|') as [string, string]
      return { source: s, target: t, value }
    })

    const { width, height } = svgSize

    const svg = d3.select(svgEl)
    svg.selectAll('*').remove()
    svg.attr('viewBox', `0 0 ${width} ${height}`).attr('preserveAspectRatio', 'xMidYMid meet')

    const defaultColor = d3.scaleOrdinal<string, string>(d3.schemeTableau10)
    const getColor = (id: string) => colorMap?.[id] || defaultColor(id)

    // Tooltip div
    const tooltip = d3
      .select(containerRef.current)
      .append('div')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('background', 'rgba(0,0,0,0.8)')
      .style('color', '#fff')
      .style('padding', '6px 10px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('opacity', 0)
      .style('transition', 'opacity 0.15s')
      .style('z-index', 10)

    const simulation = d3
      .forceSimulation<SimNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .distance(80)
          .strength(0.7),
      )
      .force('charge', d3.forceManyBody().strength(-220))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(28))

    const g = svg.append('g')

    const link = g
      .append('g')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.45)
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', (d) => 1 + Math.min(8, Math.sqrt(Number(d.value) || 1)))

    const node = g
      .append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .style('cursor', onNodeClick ? 'pointer' : 'grab')
      .call(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (d3.drag() as any)
          .on('start', (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, d: SimNode) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, d: SimNode) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>, d: SimNode) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          }),
      )

    const circles = node
      .append('circle')
      .attr('r', (d) => 10 + Math.min(18, Math.sqrt(d.count)))
      .attr('fill', (d) => getColor(d.id))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .style('transition', 'r 0.15s ease')

    if (onNodeClick) {
      node.on('click', (_, d) => onNodeClick(d.id))
    }

    // Hover effects
    node
      .on('mouseenter', (_event, d) => {
        const neighbors = new Set<string>()
        links.forEach((l) => {
          const src: string = typeof l.source === 'object' ? l.source.id : l.source as string
          const tgt: string = typeof l.target === 'object' ? l.target.id : l.target as string
          if (src === d.id) neighbors.add(tgt)
          if (tgt === d.id) neighbors.add(src)
        })

        circles
          .transition()
          .duration(150)
          .attr('r', (n) => (n.id === d.id || neighbors.has(n.id) ? (10 + Math.min(18, Math.sqrt(n.count))) * 1.3 : 6))

        link
          .transition()
          .duration(150)
          .attr('stroke-opacity', (l) => {
            const src = typeof l.source === 'object' ? l.source.id : l.source
            const tgt = typeof l.target === 'object' ? l.target.id : l.target
            return src === d.id || tgt === d.id ? 0.9 : 0.1
          })

        tooltip
          .style('opacity', 1)
          .html(`<b>${d.id}</b><br/>${d.count} tokens`)
      })
      .on('mousemove', (event) => {
        tooltip
          .style('left', `${event.offsetX + 12}px`)
          .style('top', `${event.offsetY - 28}px`)
      })
      .on('mouseleave', () => {
        circles
          .transition()
          .duration(200)
          .attr('r', (n) => 10 + Math.min(18, Math.sqrt(n.count)))

        link.transition().duration(200).attr('stroke-opacity', 0.45)

        tooltip.style('opacity', 0)
      })

    node
      .append('text')
      .text((d) => d.id)
      .attr('x', 14)
      .attr('y', 4)
      .attr('font-size', 11)
      .attr('fill', '#555')
      .style('pointer-events', 'none')

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as SimNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimNode).y ?? 0)

      node.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    return () => {
      simulation.stop()
      tooltip.remove()
    }
  }, [safeTokens, maxNodes, onNodeClick, colorMap, svgSize])

  if (!safeTokens.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyText || ''}
      </Typography>
    )
  }

  return (
    <Box ref={containerRef} sx={{ width: '100%', overflow: 'hidden', position: 'relative' }}>
      <svg ref={ref} width="100%" height={svgSize.height} role="img" aria-label="Domain network graph" />
    </Box>
  )
}
