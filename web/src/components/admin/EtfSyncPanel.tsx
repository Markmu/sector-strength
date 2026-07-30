"use client";

import React, { useState, useCallback } from 'react';
import useSWR from 'swr';
import {
  BarChart3,
  History,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Calendar,
} from 'lucide-react';
import { adminApi } from '@/lib/api';
import { useTaskStatus, type TaskData } from '@/hooks/useTaskStatus';
import { useAuth } from '@/contexts/AuthContext';
import { useRequireAdmin } from '@/hooks/useRequireAdmin';
import { fetcher } from '@/lib/fetcher';

/** 同步记录行（与后端 AsyncTask.to_dict camelCase 契约一致） */
interface SyncRecord {
  taskId: string;
  taskType: 'sync_etf_daily' | 'backfill_etf_history';
  createdAt: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  params?: Record<string, any> | null;
  errorMessage?: string;
}

/** 同步任务类型 → 中文显示名 */
const TASK_TYPE_LABELS: Record<string, string> = {
  sync_etf_daily: 'ETF 当日份额采集',
  backfill_etf_history: 'ETF 历史数据回填',
};

/** 后端需要的过滤值：逗号分隔两种 ETF 任务 */
const ETF_TASK_TYPES = 'sync_etf_daily,backfill_etf_history';

/** SWR key：fetcher 会拼上 NEXT_PUBLIC_API_URL 前缀，必须包含 /api/v1 */
const RECORDS_SWR_KEY = `/api/v1/admin/tasks?task_types=${ETF_TASK_TYPES}&page=1&page_size=20`;

/**
 * ETF 数据同步面板组件（第 14 期 plan-03 admin UI）
 *
 * 双卡片布局，复用 admin sync 范式（FundSyncPanel 双操作 + StockTop10SyncPanel 进度条）：
 * - 卡片一：ETF 当日份额/净值采集（无参数，进度按逐 ETF 推进）
 * - 卡片二：ETF 历史数据回填（start_date ~ end_date，进度按逐日推进）
 * - 底部：共享同步记录表，按 createdAt desc 展示两类任务历史
 */
export default function EtfSyncPanel() {
  useRequireAdmin();
  const { isAdmin } = useAuth();

  // ---- 当日采集状态 ----
  const [dailyTaskId, setDailyTaskId] = useState<string | null>(null);
  const [dailyLoading, setDailyLoading] = useState(false);
  const [dailyError, setDailyError] = useState<string | null>(null);
  const [dailyProgress, setDailyProgress] = useState(0);
  const [dailyTotal, setDailyTotal] = useState(0);

  // ---- 历史回填状态 ----
  const [historyTaskId, setHistoryTaskId] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyProgress, setHistoryProgress] = useState(0);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // 同步记录表：按 taskType 过滤、created_at desc 拉取
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

  // 任务状态变化时刷新同步记录
  const refreshOnTaskChange = useCallback(() => {
    refreshRecords();
  }, [refreshRecords]);

  // ---- 当日采集回调 ----
  const handleDailyComplete = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (_task: TaskData) => {
      setDailyLoading(false);
      setDailyTaskId(null);
      refreshOnTaskChange();
      showToast('success', 'ETF 当日份额采集完成');
    },
    [refreshOnTaskChange, showToast]
  );

  const handleDailyFailed = useCallback(
    (task: TaskData) => {
      setDailyLoading(false);
      setDailyTaskId(null);
      setDailyError(task.errorMessage || '未知错误');
      refreshOnTaskChange();
      showToast('error', `采集失败: ${task.errorMessage || '未知错误'}`);
    },
    [refreshOnTaskChange, showToast]
  );

  const handleDailyProgress = useCallback((task: TaskData) => {
    setDailyProgress(task.progress);
    setDailyTotal(task.total);
  }, []);

  // 轮询当日采集任务
  useTaskStatus(dailyTaskId, {
    enabled: !!dailyTaskId,
    pollInterval: 2000,
    onComplete: handleDailyComplete,
    onFailed: handleDailyFailed,
    onProgress: handleDailyProgress,
  });

  const startDailySync = async () => {
    try {
      setDailyLoading(true);
      setDailyError(null);
      setDailyProgress(0);
      setDailyTotal(0);

      const response = await adminApi.initEtfDaily();
      const newTaskId = response.data?.task_id;

      if (!newTaskId) {
        throw new Error('未返回任务 ID');
      }

      setDailyTaskId(newTaskId);
      refreshOnTaskChange();
    } catch (error) {
      const msg = (error as Error).message;
      setDailyError(msg);
      setDailyLoading(false);
      showToast('error', `创建采集任务失败: ${msg}`);
    }
  };

  // ---- 历史回填回调 ----
  const handleHistoryComplete = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (_task: TaskData) => {
      setHistoryLoading(false);
      setHistoryTaskId(null);
      refreshOnTaskChange();
      showToast('success', 'ETF 历史数据回填完成');
    },
    [refreshOnTaskChange, showToast]
  );

  const handleHistoryFailed = useCallback(
    (task: TaskData) => {
      setHistoryLoading(false);
      setHistoryTaskId(null);
      setHistoryError(task.errorMessage || '未知错误');
      refreshOnTaskChange();
      showToast('error', `回填失败: ${task.errorMessage || '未知错误'}`);
    },
    [refreshOnTaskChange, showToast]
  );

  const handleHistoryProgress = useCallback((task: TaskData) => {
    setHistoryProgress(task.progress);
    setHistoryTotal(task.total);
  }, []);

  // 轮询历史回填任务
  useTaskStatus(historyTaskId, {
    enabled: !!historyTaskId,
    pollInterval: 2000,
    onComplete: handleHistoryComplete,
    onFailed: handleHistoryFailed,
    onProgress: handleHistoryProgress,
  });

  const startHistorySync = async () => {
    // 前端只做必填校验；格式（YYYY-MM-DD 由 input[type=date] 保证）、范围上限由后端校验
    if (!startDate || !endDate) {
      showToast('error', '请选择起止日期');
      return;
    }
    if (startDate > endDate) {
      showToast('error', '开始日期不能晚于结束日期');
      return;
    }

    try {
      setHistoryLoading(true);
      setHistoryError(null);
      setHistoryProgress(0);
      setHistoryTotal(0);

      const response = await adminApi.initEtfHistory(startDate, endDate);
      const newTaskId = response.data?.task_id;

      if (!newTaskId) {
        throw new Error('未返回任务 ID');
      }

      setHistoryTaskId(newTaskId);
      refreshOnTaskChange();
    } catch (error) {
      const msg = (error as Error).message;
      setHistoryError(msg);
      setHistoryLoading(false);
      showToast('error', `创建回填任务失败: ${msg}`);
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

  const isAnySyncRunning = dailyLoading || historyLoading;
  const dailyPercent = dailyTotal > 0 ? Math.round((dailyProgress / dailyTotal) * 100) : 0;
  const historyPercent =
    historyTotal > 0 ? Math.round((historyProgress / historyTotal) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Toast 通知 */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-md px-4 py-3 rounded-lg shadow-lg border ${
            toast.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          <div className="flex items-center gap-2">
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600" />
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

      {/* ETF 当日份额采集区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">ETF 当日份额采集</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          从 Tushare 拉取当日全量 ETF 的份额/净值，计算份额变化（share_change）与资金流向估算（net_inflow）后写入 etf_daily。
        </p>

        <div className="flex items-center gap-4">
          <button
            onClick={startDailySync}
            disabled={isAnySyncRunning}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {dailyLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>采集…（{dailyProgress} / {dailyTotal}）</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>手动采集</span>
              </>
            )}
          </button>
        </div>

        {/* 进度展示 */}
        {dailyLoading && dailyTotal > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-muted-foreground">
                采集中…（{dailyProgress} / {dailyTotal}）
              </span>
              <span className="text-sm text-muted-foreground">{dailyPercent}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-primary rounded-full h-2 transition-all duration-300"
                style={{ width: `${dailyPercent}%` }}
              />
            </div>
          </div>
        )}

        {dailyError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            {dailyError}
          </div>
        )}
      </div>

      {/* ETF 历史数据回填区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <History className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">ETF 历史数据回填</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          按日期范围逐日复用同口径采集方法回填 etf_daily（on_conflict 覆盖），保证趋势曲线无断裂。范围上限 10 年。
        </p>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={isAnySyncRunning}
              aria-label="开始日期"
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <span className="text-sm text-muted-foreground">至</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={isAnySyncRunning}
              aria-label="结束日期"
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <button
            onClick={startHistorySync}
            disabled={isAnySyncRunning || !startDate || !endDate}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {historyLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>回填…（{historyProgress} / {historyTotal}）</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>开始回填</span>
              </>
            )}
          </button>
        </div>

        {/* 进度展示 */}
        {historyLoading && historyTotal > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-muted-foreground">
                回填中…（{historyProgress} / {historyTotal}）
              </span>
              <span className="text-sm text-muted-foreground">{historyPercent}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-primary rounded-full h-2 transition-all duration-300"
                style={{ width: `${historyPercent}%` }}
              />
            </div>
          </div>
        )}

        {historyError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            {historyError}
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
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">任务</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">参数</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">状态</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">详情</th>
                </tr>
              </thead>
              <tbody>
                {syncRecords.map((record) => {
                  const params = record.params || {};
                  const paramText = record.taskType === 'backfill_etf_history'
                    ? params.start_date && params.end_date
                      ? `${params.start_date} ~ ${params.end_date}`
                      : '-'
                    : '-';
                  return (
                    <tr key={record.taskId} className="border-b border-border last:border-0">
                      <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                        {record.createdAt ? new Date(record.createdAt).toLocaleString('zh-CN') : '-'}
                      </td>
                      <td className="px-6 py-3">
                        {TASK_TYPE_LABELS[record.taskType] ?? record.taskType}
                      </td>
                      <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                        {paramText}
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
    completed: { color: 'bg-green-100 text-green-700', label: '已完成' },
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
