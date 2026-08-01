"use client";

import React, { useState, useCallback } from 'react';
import useSWR from 'swr';
import {
  Flame,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
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
  taskType: 'sync_limit_data';
  createdAt: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  params?: Record<string, any> | null;
  errorMessage?: string;
}

/** 任务类型 → 中文显示名 */
const TASK_TYPE_LABELS: Record<string, string> = {
  sync_limit_data: '涨停专题同步',
};

const LIMIT_TASK_TYPES = 'sync_limit_data';

const RECORDS_SWR_KEY = `/api/v1/admin/tasks?task_types=${LIMIT_TASK_TYPES}&page=1&page_size=20`;

/**
 * 涨停专题数据同步面板
 *
 * 单卡片布局：日期选择（可选）+ 同步按钮 + 进度 + 历史记录表。
 * 一次同步 limit_list_d / limit_step / limit_cpt_list 三张表。
 */
export default function LimitSyncPanel() {
  useRequireAdmin();
  const { isAdmin } = useAuth();

  const [taskId, setTaskId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [tradeDate, setTradeDate] = useState('');

  // 同步记录表
  const {
    data: tasksData,
    isLoading: recordsLoading,
    mutate: refreshRecords,
  } = useSWR<{ tasks: SyncRecord[]; total: number; page: number }>(
    RECORDS_SWR_KEY,
    fetcher
  );

  const syncRecords = tasksData?.tasks ?? [];

  // Toast
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

  // ---- 回调 ----
  const handleComplete = useCallback(
    (_task: TaskData) => {
      setLoading(false);
      setTaskId(null);
      refreshOnTaskChange();
      showToast('success', '涨停专题同步完成');
    },
    [refreshOnTaskChange, showToast]
  );

  const handleFailed = useCallback(
    (task: TaskData) => {
      setLoading(false);
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

  // 轮询任务
  useTaskStatus(taskId, {
    enabled: !!taskId,
    pollInterval: 2000,
    onComplete: handleComplete,
    onFailed: handleFailed,
    onProgress: handleProgress,
  });

  const startSync = async () => {
    try {
      setLoading(true);
      setError(null);
      setProgress(0);
      setTotal(0);

      // tradeDate 统一去横杠（YYYYMMDD）
      const normalizedDate = tradeDate ? tradeDate.replace(/-/g, '') : undefined;
      const response = await adminApi.initLimit(normalizedDate);
      const newTaskId = response.data?.task_id;

      if (!newTaskId) {
        throw new Error('未返回任务 ID');
      }

      setTaskId(newTaskId);
      refreshOnTaskChange();
    } catch (err) {
      const msg = (err as Error).message;
      setError(msg);
      setLoading(false);
      showToast('error', `创建同步任务失败: ${msg}`);
    }
  };

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500">
        <AlertCircle className="mr-2" size={20} />
        需要管理员权限
      </div>
    );
  }

  const statusBadge = (status: SyncRecord['status']) => {
    const map: Record<SyncRecord['status'], { color: string; label: string; Icon: React.ComponentType<{ size?: number; className?: string }> }> = {
      completed: { color: 'text-green-600', label: '完成', Icon: CheckCircle2 },
      running: { color: 'text-blue-600', label: '运行中', Icon: Loader2 },
      pending: { color: 'text-gray-500', label: '等待中', Icon: Loader2 },
      failed: { color: 'text-red-600', label: '失败', Icon: XCircle },
      cancelled: { color: 'text-gray-400', label: '已取消', Icon: XCircle },
    };
    const { color, label, Icon } = map[status] ?? map.pending;
    const spin = status === 'running' || status === 'pending';
    return (
      <span className={`inline-flex items-center gap-1 ${color}`}>
        <Icon size={14} className={spin ? 'animate-spin' : ''} />
        {label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 rounded-lg px-4 py-3 shadow-lg ${
            toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'
          } text-white`}
        >
          {toast.message}
        </div>
      )}

      {/* 同步卡片 */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100">
            <Flame className="text-orange-600" size={22} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">涨停专题数据同步</h3>
            <p className="text-sm text-gray-500">
              同步涨跌停明细（limit_list_d）、连板天梯（limit_step）、涨停最强板块（limit_cpt_list）三张表
            </p>
          </div>
        </div>

        {/* 日期选择 */}
        <div className="mb-4 flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <Calendar size={16} />
            交易日（可选）
          </label>
          <input
            type="date"
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
            disabled={loading}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <span className="text-xs text-gray-400">留空则同步最新交易日</span>
        </div>

        {/* 同步按钮 */}
        <button
          onClick={startSync}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-orange-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-orange-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              同步中...
            </>
          ) : (
            <>
              <Flame size={16} />
              开始同步
            </>
          )}
        </button>

        {/* 进度 */}
        {loading && total > 0 && (
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-gray-500">
              <span>进度</span>
              <span>
                {progress} / {total}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full rounded-full bg-orange-500 transition-all"
                style={{ width: `${total > 0 ? (progress / total) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}

        {/* 错误 */}
        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* 历史记录表 */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-gray-900">同步记录</h3>
        {recordsLoading ? (
          <div className="flex items-center justify-center py-8 text-gray-400">
            <Loader2 className="animate-spin" size={20} />
          </div>
        ) : syncRecords.length === 0 ? (
          <div className="py-8 text-center text-sm text-gray-400">暂无同步记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="pb-2 pr-4 font-medium">时间</th>
                  <th className="pb-2 pr-4 font-medium">类型</th>
                  <th className="pb-2 pr-4 font-medium">状态</th>
                  <th className="pb-2 pr-4 font-medium">参数</th>
                  <th className="pb-2 font-medium">错误</th>
                </tr>
              </thead>
              <tbody>
                {syncRecords.map((r) => (
                  <tr key={r.taskId} className="border-b border-gray-100">
                    <td className="py-2 pr-4 text-gray-600">
                      {new Date(r.createdAt).toLocaleString('zh-CN')}
                    </td>
                    <td className="py-2 pr-4 text-gray-600">
                      {TASK_TYPE_LABELS[r.taskType] || r.taskType}
                    </td>
                    <td className="py-2 pr-4">{statusBadge(r.status)}</td>
                    <td className="py-2 pr-4 text-gray-500">
                      {r.params?.trade_date
                        ? `trade_date=${r.params.trade_date}`
                        : '最新交易日'}
                    </td>
                    <td className="py-2 text-red-500">
                      {r.errorMessage || '-'}
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
