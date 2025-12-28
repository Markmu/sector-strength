"use client";

import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Eye,
  Loader2,
} from 'lucide-react';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import AdminSidebar from '@/components/admin/AdminSidebar';
import AdminStatsCard, { StatsColor } from '@/components/admin/panels/AdminStatsCard';
import { tasksApi, type TaskStatus } from '@/lib/api';

/**
 * 任务统计数据类型
 */
interface TaskStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  total: number;
}

/**
 * 任务列表项类型
 */
interface TaskItem {
  taskId: string;
  taskType: string;
  status: TaskStatus;
  progress: number;
  total: number;
  percent: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

/**
 * 统计卡片配置类型
 */
interface StatsCardConfig {
  title: string;
  value: number;
  icon: typeof LayoutDashboard;
  color: StatsColor;
  trend?: string;
}

/**
 * 管理员仪表板组件
 *
 * 显示系统概览、任务统计和最近任务列表
 * 用于 /admin 首页
 *
 * 优化：
 * - 使用 useRef 存储数据，避免不必要的重渲染
 * - 轮询间隔 10 秒，减少服务器压力
 * - 数据更新时平滑替换，不重新渲染组件
 */
export default function AdminDashboard() {
  const router = useRouter();

  // 使用 useRef 存储数据，避免更新时触发重渲染
  const statsRef = useRef<TaskStats | null>(null);
  const recentTasksRef = useRef<TaskItem[]>([]);

  // 只用 state 来触发渲染（首次加载或错误状态）
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 使用 ref 跟踪是否已初始化，避免刷新时重新加载
  const isInitializedRef = useRef(false);

  // 跟踪正在进行的请求，避免重复请求
  const fetchingRef = useRef(false);

  // 获取任务统计数据
  const fetchStats = useCallback(async () => {
    try {
      const response = await tasksApi.getTaskStats();
      statsRef.current = response.data as TaskStats;
      // 触发轻量级更新
      setError(null);
    } catch (err) {
      console.error('Failed to fetch task stats:', err);
      if (!isInitializedRef.current) {
        setError('无法获取统计数据');
      }
    }
  }, []);

  // 获取最近任务列表
  const fetchRecentTasks = useCallback(async () => {
    try {
      const response = await tasksApi.listTasks({ page: 1, page_size: 5 });
      recentTasksRef.current = response.data?.tasks || [];
      // 触发轻量级更新
      setError(null);
    } catch (err) {
      console.error('Failed to fetch recent tasks:', err);
      if (!isInitializedRef.current) {
        setError('无法获取任务列表');
      }
    }
  }, []);

  // 初始化和轮询
  useEffect(() => {
    // 防止重复初始化
    if (isInitializedRef.current) return;

    const init = async () => {
      setIsInitialLoading(true);

      // 直接调用，不依赖 fetchData
      if (fetchingRef.current) {
        console.log('Fetch already in progress during init, skipping...');
        return;
      }

      fetchingRef.current = true;
      try {
        await fetchStats();
        await fetchRecentTasks();
      } finally {
        fetchingRef.current = false;
      }

      setIsInitialLoading(false);
      isInitializedRef.current = true;
    };

    init();

    // 轮询间隔 10 秒 - 直接内联请求逻辑
    const interval = setInterval(async () => {
      if (fetchingRef.current) {
        console.log('Fetch already in progress during poll, skipping...');
        return;
      }

      fetchingRef.current = true;
      try {
        await fetchStats();
        await fetchRecentTasks();
      } catch (err) {
        console.error('Polling error:', err);
      } finally {
        fetchingRef.current = false;
      }
    }, 10000);

    return () => {
      clearInterval(interval);
      fetchingRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 只在组件挂载时执行一次

  // 从 ref 获取当前值
  const stats = statsRef.current;
  const recentTasks = recentTasksRef.current;

  // 使用 useMemo 优化统计卡片配置，只在 stats 变化时重新创建
  const statsCards = useMemo((): StatsCardConfig[] => [
    {
      title: '总任务数',
      value: stats?.total || 0,
      icon: Activity,
      color: 'blue',
    },
    {
      title: '运行中',
      value: stats?.running || 0,
      icon: Clock,
      color: 'yellow',
    },
    {
      title: '失败任务',
      value: stats?.failed || 0,
      icon: AlertCircle,
      color: 'red',
    },
    {
      title: '已完成',
      value: stats?.completed || 0,
      icon: CheckCircle,
      color: 'green',
    },
  ], [stats?.total, stats?.running, stats?.failed, stats?.completed]); // 只依赖具体数值

  // 任务状态映射
  const statusConfig: Record<TaskStatus, { label: string; color: string; bg: string }> = {
    pending: { label: '等待中', color: 'text-gray-700', bg: 'bg-gray-100' },
    running: { label: '运行中', color: 'text-yellow-700', bg: 'bg-yellow-100' },
    completed: { label: '已完成', color: 'text-green-700', bg: 'bg-green-100' },
    failed: { label: '失败', color: 'text-red-700', bg: 'bg-red-100' },
    cancelled: { label: '已取消', color: 'text-gray-700', bg: 'bg-gray-100' },
  };

  // 任务类型映射
  const taskTypeLabels: Record<string, string> = {
    init_sectors: '初始化板块',
    init_stocks: '初始化股票',
    init_historical_data: '初始化历史数据',
    init_sector_stocks: '初始化板块股票',
    backfill_by_date: '按日期补齐',
    backfill_by_range: '按范围补齐',
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">仪表板概览</h1>
          <p className="mt-1 text-sm text-gray-600">系统状态和任务统计</p>
        </div>

        {/* 初始加载状态 */}
        {isInitialLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600 mr-2" />
            <span className="text-gray-600">加载中...</span>
          </div>
        ) : error && !stats ? (
          <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : (
          <>
            {/* 统计卡片 */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {statsCards.map((card) => (
                <AdminStatsCard
                  key={card.title}
                  title={card.title}
                  value={card.value}
                  icon={card.icon}
                  color={card.color}
                />
              ))}
            </div>

            {/* 最近任务 */}
            <div className="rounded-lg bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">最近任务</h2>
                <button
                  onClick={() => router.push('/dashboard/admin/tasks')}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                >
                  <Eye className="h-4 w-4" />
                  查看全部
                </button>
              </div>

              {!recentTasks || recentTasks.length === 0 ? (
                <div className="py-8 text-center text-sm text-gray-500">
                  暂无任务记录
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead>
                      <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase text-gray-500">
                        <th className="pb-3 pl-2">任务类型</th>
                        <th className="pb-3">状态</th>
                        <th className="pb-3">进度</th>
                        <th className="pb-3 pr-2 text-right">创建时间</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {recentTasks.map((task) => {
                        const statusInfo = statusConfig[task.status];
                        return (
                          <tr
                            key={task.taskId}
                            className="cursor-pointer hover:bg-gray-50"
                            onClick={() => router.push(`/dashboard/admin/tasks?task=${task.taskId}`)}
                          >
                            <td className="py-3 pl-2">
                              <div className="text-sm font-medium text-gray-900">
                                {taskTypeLabels[task.taskType] || task.taskType}
                              </div>
                              <div className="text-xs text-gray-500">{task.taskId}</div>
                            </td>
                            <td className="py-3">
                              <span
                                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusInfo.bg} ${statusInfo.color}`}
                              >
                                {statusInfo.label}
                              </span>
                            </td>
                            <td className="py-3">
                              <div className="flex items-center gap-2">
                                <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
                                  <div
                                    className="h-full bg-blue-600 transition-all"
                                    style={{ width: `${task.percent}%` }}
                                  />
                                </div>
                                <span className="text-xs text-gray-600">{task.percent}%</span>
                              </div>
                              <div className="text-xs text-gray-500">
                                {task.progress} / {task.total}
                              </div>
                            </td>
                            <td className="py-3 pr-2 text-right">
                              <div className="text-sm text-gray-600">
                                {formatTime(task.createdAt)}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* 快捷操作 */}
            <div className="rounded-lg bg-gradient-to-br from-blue-50 to-purple-50 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">快捷操作</h2>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <button
                  onClick={() => router.push('/dashboard/admin/data')}
                  className="rounded-lg bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-blue-100 p-2">
                      <Activity className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">数据管理</div>
                      <div className="text-sm text-gray-600">初始化和更新数据</div>
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/dashboard/admin/tasks')}
                  className="rounded-lg bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-yellow-100 p-2">
                      <Clock className="h-5 w-5 text-yellow-600" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">任务监控</div>
                      <div className="text-sm text-gray-600">查看任务状态和日志</div>
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/dashboard/admin/users')}
                  className="rounded-lg bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-green-100 p-2">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">用户管理</div>
                      <div className="text-sm text-gray-600">管理用户和权限</div>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </AdminLayoutWithSidebar>
  );
}
