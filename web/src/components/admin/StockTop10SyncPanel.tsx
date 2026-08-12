"use client";

import React, { useState, useCallback } from 'react';
import useSWR from 'swr';
import {
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Calendar,
  Users,
} from 'lucide-react';
import { adminApi } from '@/lib/api';
import { useTaskStatus, type TaskData } from '@/hooks/useTaskStatus';
import { useAuth } from '@/contexts/AuthContext';
import { useRequireAdmin } from '@/hooks/useRequireAdmin';
import { fetcher } from '@/lib/fetcher';

/** 同步记录行 */
interface SyncRecord {
  taskId: string;
  taskType: string;
  createdAt: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  params?: Record<string, any> | null;
  errorMessage?: string;
}

/** SWR key：fetcher 会拼上 NEXT_PUBLIC_API_URL 前缀，必须包含 /api/v1 */
const RECORDS_SWR_KEY = '/api/v1/admin/tasks?task_types=sync_top10_holders&page=1&page_size=20';

/** 生成最近 N 个季度末 YYYYMMDD */
function getRecentQuarters(count: number = 8): string[] {
  const now = new Date();
  const result: string[] = [];
  let y = now.getFullYear();
  let q = Math.floor(now.getMonth() / 3); // 0=Q1, 1=Q2, 2=Q3, 3=Q4

  // Start from the last completed quarter
  q -= 1;
  if (q < 0) {
    q = 3;
    y -= 1;
  }

  for (let i = 0; i < count; i++) {
    const endMonth = (q + 1) * 3; // 3, 6, 9, 12
    const mm = String(endMonth).padStart(2, '0');
    const dd = endMonth === 3 ? '31' : endMonth === 6 ? '30' : endMonth === 9 ? '30' : '31';
    result.push(`${y}${mm}${dd}`);

    q -= 1;
    if (q < 0) {
      q = 3;
      y -= 1;
    }
  }

  return result;
}

function formatPeriod(period: string): string {
  if (period.length !== 8) return period;
  return `${period.slice(0, 4)}-${period.slice(4, 6)}-${period.slice(6, 8)}`;
}

/**
 * 股票十大流通股东同步面板组件
 *
 * 包含报告期选择器、同步按钮、进度展示、统计结果和同步记录表格。
 */
export default function StockTop10SyncPanel() {
  useRequireAdmin();
  const { isAdmin } = useAuth();

  // 同步状态
  const [taskId, setTaskId] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [periods] = useState<string[]>(() => getRecentQuarters(8));

  // 任务进度（从 useTaskStatus 回调更新）
  const [progress, setProgress] = useState<number>(0);
  const [total, setTotal] = useState<number>(0);

  // 同步记录表
  const {
    data: tasksData,
    isLoading: recordsLoading,
    mutate: refreshRecords,
  } = useSWR<{
    tasks: SyncRecord[];
    total: number;
    page: number;
  }>(RECORDS_SWR_KEY, fetcher);

  const syncRecords = tasksData?.tasks ?? [];

  // Toast 通知
  const [toast, setToast] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const showToast = useCallback((type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  }, []);

  const refreshOnTaskChange = useCallback(() => {
    refreshRecords();
  }, [refreshRecords]);

  // ---- 任务完成回调 ----
  const handleComplete = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (_task: TaskData) => {
      setSyncing(false);
      setTaskId(null);
      refreshOnTaskChange();
      showToast('success', '股票持仓同步完成');
    },
    [refreshOnTaskChange, showToast]
  );

  const handleFailed = useCallback(
    (task: TaskData) => {
      setSyncing(false);
      setTaskId(null);
      setError(task.errorMessage || '未知错误');
      refreshOnTaskChange();
      showToast('error', `同步失败: ${task.errorMessage || '未知错误'}`);
    },
    [refreshOnTaskChange, showToast]
  );

  const handleProgress = useCallback((task: TaskData) => {
    setProgress(task.progress);
    setTotal(task.total);
  }, []);

  // 轮询任务状态
  useTaskStatus(taskId, {
    enabled: !!taskId,
    pollInterval: 2000,
    onComplete: handleComplete,
    onFailed: handleFailed,
    onProgress: handleProgress,
  });

  // ---- 触发同步 ----
  const startSync = async () => {
    if (!selectedPeriod) {
      showToast('error', '请选择报告期');
      return;
    }

    try {
      setSyncing(true);
      setError(null);
      setProgress(0);
      setTotal(0);

      const response = await adminApi.initStockTop10Holders(selectedPeriod);
      const newTaskId = response.data?.task_id;

      if (!newTaskId) {
        throw new Error('未返回任务 ID');
      }

      setTaskId(newTaskId);
      refreshOnTaskChange();
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      setSyncing(false);
      showToast('error', `创建同步任务失败: ${msg}`);
    }
  };

  // ---- 渲染 ----
  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
          <p className="text-muted-foreground">您没有权限访问此页面</p>
        </div>
      </div>
    );
  }

  // 计算进度百分比
  const progressPercent = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Toast 通知 */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-md px-4 py-3 rounded-lg shadow-lg border ${
            toast.type === 'success'
              ? 'bg-fall/10 border-fall/30 text-fall'
              : 'bg-rise/10 border-rise/30 text-rise'
          }`}
        >
          <div className="flex items-center gap-2">
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-fall" />
            ) : (
              <XCircle className="w-5 h-5 text-rise" />
            )}
            <span className="text-sm font-medium">{toast.message}</span>
            <button
              onClick={() => setToast(null)}
              className="ml-2 text-current opacity-50 hover:opacity-100"
            >
              &times;
            </button>
          </div>
        </div>
      )}

      {/* 股票持仓同步区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">股票持仓同步</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          从 Tushare 拉取指定报告期全市场股票的十大流通股东数据，采用先删后写策略保证幂等性。
        </p>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              disabled={syncing}
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">选择报告期</option>
              {periods.map((p) => (
                <option key={p} value={p}>
                  {formatPeriod(p)}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={startSync}
            disabled={syncing || !selectedPeriod}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {syncing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>同步中…（{progress} / {total}）</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>同步</span>
              </>
            )}
          </button>
        </div>

        {/* 进度展示 */}
        {syncing && total > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-muted-foreground">
                同步中…（{progress} / {total}）
              </span>
              <span className="text-sm text-muted-foreground">{progressPercent}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-primary rounded-full h-2 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        {error && (
          <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}
      </div>

      {/* 同步记录表格 */}
      <div className="bg-card rounded-lg shadow-sm border border-border">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">同步记录</h3>
          <button
            onClick={() => refreshOnTaskChange()}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            title="刷新"
          >
            <RefreshCw className="w-4 h-4" />
            <span>刷新</span>
          </button>
        </div>
        {recordsLoading && syncRecords.length === 0 ? (
          <div className="px-6 py-8 flex items-center justify-center text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            加载中...
          </div>
        ) : syncRecords.length === 0 ? (
          <div className="px-6 py-8 text-center text-muted-foreground">
            暂无同步记录
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">时间</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">报告期</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">状态</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">详情</th>
                </tr>
              </thead>
              <tbody>
                {syncRecords.map((record) => {
                  const period = record.params?.period as string | undefined;
                  return (
                    <tr key={record.taskId} className="border-b border-border last:border-0">
                      <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                        {record.createdAt ? new Date(record.createdAt).toLocaleString('zh-CN') : '-'}
                      </td>
                      <td className="px-6 py-3 text-muted-foreground">
                        {period ? formatPeriod(period) : '-'}
                      </td>
                      <td className="px-6 py-3">
                        <StatusBadge status={record.status} />
                      </td>
                      <td className="px-6 py-3 text-muted-foreground max-w-xs truncate">
                        {record.status === 'failed' && record.errorMessage
                          ? record.errorMessage
                          : '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/** 状态徽章 */
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string }> = {
    pending: { color: 'bg-secondary text-foreground', label: '等待中' },
    running: { color: 'bg-primary-light text-primary', label: '运行中' },
    completed: { color: 'bg-fall/10 text-fall', label: '已完成' },
    failed: { color: 'bg-destructive/10 text-destructive', label: '失败' },
    cancelled: { color: 'bg-secondary text-muted-foreground', label: '已取消' },
  };

  const { color, label } = config[status] || { color: 'bg-secondary text-muted-foreground', label: status };

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
      {label}
    </span>
  );
}
