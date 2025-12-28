"use client";

import React from 'react';
import { LucideIcon } from 'lucide-react';

/**
 * 统计卡片组件 - 显示单个统计数据
 *
 * 用于管理员仪表板首页，显示任务统计、用户统计等
 *
 * @example
 * ```tsx
 * <AdminStatsCard
 *   title="总任务数"
 *   value={156}
 *   icon={LayoutDashboard}
 *   color="blue"
 *   trend="+5"
 * />
 * ```
 */

export type StatsColor = 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'gray';

interface AdminStatsCardProps {
  /** 卡片标题 */
  title: string;
  /** 统计数值 */
  value: number | string;
  /** 图标 */
  icon: LucideIcon;
  /** 颜色主题 */
  color?: StatsColor;
  /** 趋势标签（可选） */
  trend?: string;
  /** 是否加载中 */
  loading?: boolean;
  /** 点击回调 */
  onClick?: () => void;
  /** 自定义类名 */
  className?: string;
}

/**
 * 颜色映射配置
 */
const colorConfig: Record<StatsColor, {
  bg: string;
  text: string;
  iconBg: string;
  iconText: string;
  border: string;
}> = {
  blue: {
    bg: 'bg-blue-50',
    text: 'text-blue-900',
    iconBg: 'bg-blue-100',
    iconText: 'text-blue-600',
    border: 'border-blue-200',
  },
  green: {
    bg: 'bg-green-50',
    text: 'text-green-900',
    iconBg: 'bg-green-100',
    iconText: 'text-green-600',
    border: 'border-green-200',
  },
  red: {
    bg: 'bg-red-50',
    text: 'text-red-900',
    iconBg: 'bg-red-100',
    iconText: 'text-red-600',
    border: 'border-red-200',
  },
  yellow: {
    bg: 'bg-yellow-50',
    text: 'text-yellow-900',
    iconBg: 'bg-yellow-100',
    iconText: 'text-yellow-600',
    border: 'border-yellow-200',
  },
  purple: {
    bg: 'bg-purple-50',
    text: 'text-purple-900',
    iconBg: 'bg-purple-100',
    iconText: 'text-purple-600',
    border: 'border-purple-200',
  },
  gray: {
    bg: 'bg-gray-50',
    text: 'text-gray-900',
    iconBg: 'bg-gray-100',
    iconText: 'text-gray-600',
    border: 'border-gray-200',
  },
};

export default function AdminStatsCard({
  title,
  value,
  icon: Icon,
  color = 'blue',
  trend,
  loading = false,
  onClick,
  className = '',
}: AdminStatsCardProps) {
  const config = colorConfig[color];

  return (
    <div
      className={`
        relative overflow-hidden rounded-xl border ${config.border}
        bg-white p-6 shadow-sm transition-all duration-200
        ${onClick ? 'cursor-pointer hover:shadow-md' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {/* 背景装饰 */}
      <div className={`absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-10 ${config.iconBg}`} />

      {/* 内容 */}
      <div className="relative">
        {/* 标题行 */}
        <div className="flex items-center justify-between">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${config.iconBg}`}>
            <Icon className={`h-5 w-5 ${config.iconText}`} />
          </div>
          {trend && (
            <span className={`text-sm font-medium ${config.text}`}>
              {trend}
            </span>
          )}
        </div>

        {/* 数值 */}
        <div className="mt-4">
          {loading ? (
            <div className="h-8 w-20 animate-pulse rounded bg-gray-200" />
          ) : (
            <p className={`text-3xl font-bold ${config.text}`}>
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
          )}
          <p className="mt-1 text-sm text-gray-600">{title}</p>
        </div>
      </div>
    </div>
  );
}
