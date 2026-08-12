'use client'

/**
 * 迷你折线图（10 期 plan-02，ADR-6 / AC-05/07/11）
 *
 * 轻量 SVG 自绘--**不复用 echarts**（趋势榜每页 20 行 × 20 echarts 实例渲染开销过大；
 * sparkline 无交互、无坐标轴，SVG polyline 最轻量）。
 *
 * - 横轴旧→新（values 已按月份升序传入）
 * - 含 0 断档点（断档股，AC-07）
 * - 单点场景（values.length===1，AC-11 单月数据）用 circle 兜底渲染
 *
 * data-testid：由调用方传入（如 `broker-trend-sparkline-${symbol}`），便于 E2E 定位。
 */
import React from 'react'

export interface SparklineProps {
  /** 数值序列（monthlySeries 的 brokerCount，已旧→新升序） */
  values: number[]
  width?: number
  height?: number
  /** 默认 currentColor（随主题） */
  color?: string
  testId?: string
}

export default function Sparkline({
  values,
  width = 80,
  height = 24,
  color = 'currentColor',
  testId,
}: SparklineProps) {
  if (!values || values.length === 0) {
    return (
      <div
        style={{ width, height }}
        className="inline-block"
        data-testid={testId}
      />
    )
  }

  const max = Math.max(...values, 1) // 至少 1 防除零
  const min = Math.min(...values, 0)
  const range = max - min || 1
  const stepX = values.length > 1 ? width / (values.length - 1) : 0

  const points = values
    .map((v, i) => {
      const x = i * stepX
      const y = height - ((v - min) / range) * height
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  // 单点场景：polyline 退化为点，加 circle 兜底确保可见（AC-11）
  const isSinglePoint = values.length === 1
  const singlePoint = isSinglePoint
    ? {
        cx: 0,
        cy: height - ((values[0] - min) / range) * height,
      }
    : null

  return (
    <svg
      width={width}
      height={height}
      className="inline-block align-middle"
      data-testid={testId}
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
      />
      {singlePoint && (
        <circle
          cx={width / 2}
          cy={singlePoint.cy}
          r={1.5}
          fill={color}
        />
      )}
    </svg>
  )
}
