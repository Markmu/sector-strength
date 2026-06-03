"use client";

import React, { useState, useCallback } from 'react';
import {
  Database,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ChevronDown,
  Calendar,
  TrendingUp,
} from 'lucide-react';
import { adminApi } from '@/lib/api';
import { useTaskStatus, type TaskData } from '@/hooks/useTaskStatus';
import { useAuth } from '@/contexts/AuthContext';
import { useRequireAdmin } from '@/hooks/useRequireAdmin';

/** 同步记录行 */
interface SyncRecord {
  id: string;
  taskType: 'sync_fund_basic' | 'sync_fund_portfolio';
  createdAt: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  result?: {
    added?: number;
    updated?: number;
    failed?: number;
  } | null;
  errorMessage?: string;
  period?: string;
}

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
 * 基金同步面板组件
 *
 * 包含基金基本信息同步、基金持仓明细同步、同步记录表格。
 */
export default function FundSyncPanel() {
  useRequireAdmin();
  const { isAdmin } = useAuth();

  // 基金基本信息同步状态
  const [basicTaskId, setBasicTaskId] = useState<string | null>(null);
  const [basicLoading, setBasicLoading] = useState(false);
  const [basicError, setBasicError] = useState<string | null>(null);

  // 基金持仓同步状态
  const [portfolioTaskId, setPortfolioTaskId] = useState<string | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [periods] = useState<string[]>(() => getRecentQuarters(8));

  // 同步记录表
  const [syncRecords, setSyncRecords] = useState<SyncRecord[]>([]);

  // Toast 通知
  const [toast, setToast] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const showToast = useCallback((type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  }, []);

  const addSyncRecord = useCallback((record: SyncRecord) => {
    setSyncRecords((prev) => [record, ...prev]);
  }, []);

  // ---- 基金基本信息同步 ----
  const handleBasicComplete = useCallback(
    (task: TaskData) => {
      setBasicLoading(false);
      setBasicTaskId(null);

      // 解析结果
      const _result: SyncRecord['result'] = null;
      try {
        // TaskData 不直接包含 result 字段，需要从 logs 或其他方式获取
        // 实际结果存于 AsyncTask 的 result 列中
        // 这里先放占位，后续通过 listTasks 刷新
      } catch {
        // ignore
      }

      addSyncRecord({
        id: task.taskId,
        taskType: 'sync_fund_basic',
        createdAt: task.createdAt || new Date().toISOString(),
        status: 'completed',
        result: _result,
      });

      showToast('success', '基金基本信息同步完成');
    },
    [addSyncRecord, showToast]
  );

  const handleBasicFailed = useCallback(
    (task: TaskData) => {
      setBasicLoading(false);
      setBasicTaskId(null);

      addSyncRecord({
        id: task.taskId,
        taskType: 'sync_fund_basic',
        createdAt: task.createdAt || new Date().toISOString(),
        status: 'failed',
        errorMessage: task.errorMessage,
      });

      showToast('error', `同步失败: ${task.errorMessage || '未知错误'}`);
    },
    [addSyncRecord, showToast]
  );

  // 轮询基金基本信息任务
  useTaskStatus(basicTaskId, {
    enabled: !!basicTaskId,
    pollInterval: 3000,
    onComplete: handleBasicComplete,
    onFailed: handleBasicFailed,
  });

  const startBasicSync = async () => {
    try {
      setBasicLoading(true);
      setBasicError(null);

      const response = await adminApi.initFundBasic();
      const taskId = response.data?.task_id;

      if (!taskId) {
        throw new Error('未返回任务 ID');
      }

      setBasicTaskId(taskId);

      addSyncRecord({
        id: taskId,
        taskType: 'sync_fund_basic',
        createdAt: new Date().toISOString(),
        status: 'running',
      });
    } catch (error) {
      const msg = (error as Error).message;
      setBasicError(msg);
      setBasicLoading(false);
      showToast('error', `创建同步任务失败: ${msg}`);
    }
  };

  // ---- 基金持仓明细同步 ----
  const handlePortfolioComplete = useCallback(
    (task: TaskData) => {
      setPortfolioLoading(false);
      setPortfolioTaskId(null);

      addSyncRecord({
        id: task.taskId,
        taskType: 'sync_fund_portfolio',
        createdAt: task.createdAt || new Date().toISOString(),
        status: 'completed',
        period: task.params?.period,
      });

      showToast('success', '基金持仓明细同步完成');
    },
    [addSyncRecord, showToast]
  );

  const handlePortfolioFailed = useCallback(
    (task: TaskData) => {
      setPortfolioLoading(false);
      setPortfolioTaskId(null);

      addSyncRecord({
        id: task.taskId,
        taskType: 'sync_fund_portfolio',
        createdAt: task.createdAt || new Date().toISOString(),
        status: 'failed',
        errorMessage: task.errorMessage,
        period: task.params?.period,
      });

      showToast('error', `同步失败: ${task.errorMessage || '未知错误'}`);
    },
    [addSyncRecord, showToast]
  );

  // 轮询基金持仓任务
  useTaskStatus(portfolioTaskId, {
    enabled: !!portfolioTaskId,
    pollInterval: 3000,
    onComplete: handlePortfolioComplete,
    onFailed: handlePortfolioFailed,
  });

  const startPortfolioSync = async (period: string) => {
    if (!period) {
      showToast('error', '请选择报告期');
      return;
    }

    try {
      setPortfolioLoading(true);
      setPortfolioError(null);

      const response = await adminApi.initFundPortfolio(period);
      const taskId = response.data?.task_id;

      if (!taskId) {
        throw new Error('未返回任务 ID');
      }

      setPortfolioTaskId(taskId);

      addSyncRecord({
        id: taskId,
        taskType: 'sync_fund_portfolio',
        createdAt: new Date().toISOString(),
        status: 'running',
        period,
      });
    } catch (error) {
      const msg = (error as Error).message;
      setPortfolioError(msg);
      setPortfolioLoading(false);
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

  const isAnySyncRunning = basicLoading || portfolioLoading;

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

      {/* 基金基本信息同步区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">基金基本信息同步</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          从 Tushare 拉取场内+场外基金基本信息，通过 upsert 写入 funds 表。
        </p>

        <div className="flex items-center gap-4">
          <button
            onClick={startBasicSync}
            disabled={isAnySyncRunning}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {basicLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>同步中...</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>手动同步</span>
              </>
            )}
          </button>

          {basicLoading && basicTaskId && (
            <span className="text-sm text-muted-foreground">
              任务 {basicTaskId.slice(0, 12)}... 运行中
            </span>
          )}
        </div>

        {basicError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            {basicError}
          </div>
        )}
      </div>

      {/* 基金持仓明细同步区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">基金持仓明细同步</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          从 Tushare 拉取指定报告期的基金持仓明细，采用&ldquo;先 INSERT 后 DELETE&rdquo;策略写入。
        </p>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              disabled={isAnySyncRunning}
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
            onClick={() => startPortfolioSync(selectedPeriod)}
            disabled={isAnySyncRunning || !selectedPeriod}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {portfolioLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>同步中...</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>同步指定报告期</span>
              </>
            )}
          </button>

          {/* 同步今日新披露按钮（快捷入口） */}
          {periods.length > 0 && (
            <button
              onClick={() => startPortfolioSync(periods[0])}
              disabled={isAnySyncRunning}
              className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:bg-secondary hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={`同步最新季度 ${formatPeriod(periods[0])}`}
            >
              <ChevronDown className="w-4 h-4" />
              <span>同步最新季度 ({formatPeriod(periods[0])})</span>
            </button>
          )}
        </div>

        {portfolioLoading && portfolioTaskId && (
          <div className="mt-3 text-sm text-muted-foreground">
            任务 {portfolioTaskId.slice(0, 12)}... 运行中
          </div>
        )}

        {portfolioError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            {portfolioError}
          </div>
        )}
      </div>

      {/* 同步记录表格 */}
      <div className="bg-card rounded-lg shadow-sm border border-border">
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold text-foreground">同步记录</h3>
        </div>
        {syncRecords.length === 0 ? (
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
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">报告期</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">结果</th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">详情</th>
                </tr>
              </thead>
              <tbody>
                {syncRecords.map((record) => (
                  <tr key={record.id} className="border-b border-border last:border-0">
                    <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                      {new Date(record.createdAt).toLocaleString('zh-CN')}
                    </td>
                    <td className="px-6 py-3">
                      {record.taskType === 'sync_fund_basic' ? '基金基本信息' : '基金持仓'}
                    </td>
                    <td className="px-6 py-3 text-muted-foreground">
                      {record.period ? formatPeriod(record.period) : '-'}
                    </td>
                    <td className="px-6 py-3">
                      <StatusBadge status={record.status} />
                    </td>
                    <td className="px-6 py-3 text-muted-foreground max-w-xs truncate">
                      {record.status === 'failed' && record.errorMessage
                        ? record.errorMessage
                        : record.result
                          ? `新增 ${record.result.added ?? '-'} / 更新 ${record.result.updated ?? '-'} / 失败 ${record.result.failed ?? '-'}`
                          : '-'}
                    </td>
                  </tr>
                ))}
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
