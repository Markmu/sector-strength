"use client";

/**
 * 指数数据同步面板（第 15 期 plan-04 Task 11）
 *
 * 数据管理页「指数数据」Tab 内容，范式严格对齐 EtfSyncPanel.tsx：
 * - 三同步卡片（清单/历史/当日）+ isAnySyncRunning 互斥锁（AC-08c）
 * - useTaskStatus 轮询进度（AC-08c）
 * - 失败时显示错误 + 重试（AC-08d）
 * - 关注管理区：当前关注清单 + 名称/代码模糊搜索添加 + 保存（AC-07）
 *   搜索走 /index-monitor/search（查 index_basic 全表），默认展示 15 条；
 *   选中即加入 pending，点保存全量提交。
 * - 同步记录表（SWR 拉 task_types=sync_index_basic,backfill_index_history,sync_index_daily）
 */
import React, { useState, useCallback } from 'react';
import useSWR from 'swr';
import {
  Database,
  BarChart3,
  History,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Calendar,
  Star,
  Search,
  X,
} from 'lucide-react';
import { adminApi, indexMonitorApi } from '@/lib/api';
import { useTaskStatus, type TaskData } from '@/hooks/useTaskStatus';
import { useAuth } from '@/contexts/AuthContext';
import { useRequireAdmin } from '@/hooks/useRequireAdmin';
import { fetcher } from '@/lib/fetcher';
import SearchDropdownInput from '@/components/ui/SearchDropdownInput';
import type { SearchDropdownOption } from '@/components/ui/SearchDropdownInput';

/** 同步记录行（与后端 AsyncTask.to_dict camelCase 契约一致） */
interface SyncRecord {
  taskId: string;
  taskType: 'sync_index_basic' | 'sync_index_daily' | 'backfill_index_history';
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
  sync_index_basic: '指数基础信息同步',
  sync_index_daily: '指数当日采集',
  backfill_index_history: '指数历史数据回填',
};

/** 后端需要的过滤值：逗号分隔三类指数任务 */
const INDEX_TASK_TYPES = 'sync_index_basic,sync_index_daily,backfill_index_history';

/** SWR key：fetcher 拼 NEXT_PUBLIC_API_URL 前缀，包含 /api/v1 */
const RECORDS_SWR_KEY = `/api/v1/admin/tasks?task_types=${INDEX_TASK_TYPES}&page=1&page_size=20`;

export default function IndexSyncPanel() {
  useRequireAdmin();
  const { isAdmin } = useAuth();

  // ---- 基础信息同步状态 ----
  const [basicTaskId, setBasicTaskId] = useState<string | null>(null);
  const [basicLoading, setBasicLoading] = useState(false);
  const [basicError, setBasicError] = useState<string | null>(null);
  const [basicProgress, setBasicProgress] = useState(0);
  const [basicTotal, setBasicTotal] = useState(0);
  const [basicSynced, setBasicSynced] = useState(false);

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

  // ---- 关注管理状态 ----
  const [pendingCodes, setPendingCodes] = useState<string[] | null>(null);
  const [savingWatchlist, setSavingWatchlist] = useState(false);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);

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

  // 当前关注列表（plan-03 /watchlist GET）
  const {
    data: watchlistData,
    isLoading: watchlistLoading,
    mutate: refreshWatchlist,
  } = useSWR<{
    success: boolean;
    data: { watchlist: Array<{ tsCode: string; name: string; market: string | null; hasValuation: boolean }> };
  }>(`/api/v1/index-monitor/watchlist`, fetcher);

  // 当前关注 ts_code 列表（pending 优先，否则用后端返回）
  const currentCodes: string[] = pendingCodes ?? (watchlistData?.data?.watchlist ?? []).map((w) => w.tsCode);

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

  // ---- 基础信息同步回调 ----
  const handleBasicComplete = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (_task: TaskData) => {
      setBasicLoading(false);
      setBasicTaskId(null);
      setBasicSynced(true);
      refreshOnTaskChange();
      refreshWatchlist();
      showToast('success', '指数基础信息同步完成');
    },
    [refreshOnTaskChange, refreshWatchlist, showToast]
  );

  const handleBasicFailed = useCallback(
    (task: TaskData) => {
      setBasicLoading(false);
      setBasicTaskId(null);
      setBasicError(task.errorMessage || '未知错误');
      refreshOnTaskChange();
      showToast('error', `同步失败: ${task.errorMessage || '未知错误'}`);
    },
    [refreshOnTaskChange, showToast]
  );

  const handleBasicProgress = useCallback((task: TaskData) => {
    setBasicProgress(task.progress);
    setBasicTotal(task.total);
  }, []);

  useTaskStatus(basicTaskId, {
    enabled: !!basicTaskId,
    pollInterval: 2000,
    onComplete: handleBasicComplete,
    onFailed: handleBasicFailed,
    onProgress: handleBasicProgress,
  });

  const startBasicSync = async () => {
    try {
      setBasicLoading(true);
      setBasicError(null);
      setBasicProgress(0);
      setBasicTotal(0);

      const response = await adminApi.initIndexBasic();
      const newTaskId = response.data?.task_id;

      if (!newTaskId) {
        throw new Error('未返回任务 ID');
      }

      setBasicTaskId(newTaskId);
      refreshOnTaskChange();
    } catch (error) {
      const msg = (error as Error).message;
      setBasicError(msg);
      setBasicLoading(false);
      showToast('error', `创建同步任务失败: ${msg}`);
    }
  };

  // ---- 当日采集回调 ----
  const handleDailyComplete = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (_task: TaskData) => {
      setDailyLoading(false);
      setDailyTaskId(null);
      refreshOnTaskChange();
      showToast('success', '指数当日采集完成');
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

      const response = await adminApi.initIndexDaily();
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
      showToast('success', '指数历史数据回填完成');
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

  useTaskStatus(historyTaskId, {
    enabled: !!historyTaskId,
    pollInterval: 2000,
    onComplete: handleHistoryComplete,
    onFailed: handleHistoryFailed,
    onProgress: handleHistoryProgress,
  });

  const startHistorySync = async () => {
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

      const response = await adminApi.initIndexHistory(startDate, endDate);
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

  // ---- 关注管理 ----
  // 模糊搜索指数（按 ts_code 前缀 / name 包含），供 SearchDropdownInput 使用。
  // 组件自带防抖与无限滚动，这里只负责把后端结果映射成 {value,label}。
  const searchIndexes = useCallback(async (keyword: string, page: number) => {
    const res = await indexMonitorApi.search(keyword, { page, pageSize: 15 });
    const payload = res.data;
    const items = payload?.data?.items ?? [];
    return {
      options: items.map((it) => ({ value: it.tsCode, label: it.name || it.tsCode })),
      total: payload?.data?.total ?? 0,
    };
  }, []);

  // 选中下拉项即加入 pending 关注列表（ts_code 来自 DB，天然合法，无需格式校验）。
  // 选中后清除输入由 SearchDropdownInput 内部完成。
  const handleSelectIndex = useCallback(
    (option: SearchDropdownOption) => {
      const code = option.value;
      if (currentCodes.includes(code)) {
        showToast('error', `${option.label}（${code}）已在关注列表`);
        return;
      }
      setPendingCodes([...currentCodes, code]);
      showToast('success', `已添加 ${option.label}（${code}），记得保存`);
    },
    [currentCodes, showToast]
  );

  const removeCode = (code: string) => {
    setPendingCodes(currentCodes.filter((c) => c !== code));
  };

  const saveWatchlist = async () => {
    const codesToSave = pendingCodes ?? currentCodes;
    try {
      setSavingWatchlist(true);
      setWatchlistError(null);
      const { data } = await indexMonitorApi.updateWatchlist(codesToSave);
      if (!data) {
        throw new Error('保存关注清单失败：服务端未返回数据');
      }
      // 后端 success=false 表示有 ts_code 在 index_basic 中不存在（静默不命中）
      if (!data.success) {
        const notFound = data.data.notFound ?? [];
        const msg = `以下指数代码未识别，请先同步指数基础信息或核对代码：${notFound.join('、')}`;
        setWatchlistError(msg);
        showToast('error', msg);
        // 不清 pendingCodes，保留让用户修正
        return;
      }
      setPendingCodes(null);
      await refreshWatchlist();
      showToast('success', `关注清单已更新（${codesToSave.length} 只）`);
    } catch (error) {
      const msg = (error as Error).message;
      setWatchlistError(msg);
      showToast('error', `保存失败: ${msg}`);
    } finally {
      setSavingWatchlist(false);
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

  const isAnySyncRunning = basicLoading || dailyLoading || historyLoading;
  const basicPercent = basicTotal > 0 ? Math.round((basicProgress / basicTotal) * 100) : 0;
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

      {/* 指数基础信息同步区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">指数基础信息同步</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          从 Tushare 拉取全量指数基础信息，预置 14 只关注指数。建议在历史回填 / 当日采集前先同步基础信息。
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
                <span>同步…（{basicProgress} / {basicTotal}）</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>手动同步</span>
              </>
            )}
          </button>
          {basicSynced && !basicLoading && (
            <span className="inline-flex items-center gap-1 text-sm text-green-600">
              <CheckCircle2 className="w-4 h-4" />
              已同步
            </span>
          )}
        </div>

        {basicLoading && basicTotal > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-muted-foreground">
                同步中…（{basicProgress} / {basicTotal}）
              </span>
              <span className="text-sm text-muted-foreground">{basicPercent}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-primary rounded-full h-2 transition-all duration-300"
                style={{ width: `${basicPercent}%` }}
              />
            </div>
          </div>
        )}

        {basicError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            {basicError}
          </div>
        )}
      </div>

      {/* 指数历史数据回填区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <History className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">指数历史数据回填</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          按日期范围逐交易日回填关注指数的 daily/dailybasic/weight 数据（on_conflict 覆盖），范围上限 10 年。
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

      {/* 指数当日采集区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">指数当日采集</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          采集关注指数当日行情 / 估值 / 权重数据，进度按逐指数推进。交易日收盘后执行。
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

      {/* 关注管理区（AC-07） */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Star className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">关注指数管理</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          管理主页监控面板的关注指数列表。在搜索框输入指数代码或名称，从下拉结果中选中添加，修改完成点击保存即全量更新。
        </p>

        {/* 添加输入区常驻：是否已同步指数基础信息不再用前端会话状态判断，
            由后端 PUT /watchlist 校验 ts_code 是否存在并返回 notFound，避免"假成功"。 */}
        <>
            {/* 添加输入：按名称/代码模糊搜索，默认展示 15 条 */}
            <div className="mb-4 max-w-md">
              <SearchDropdownInput
                placeholder="输入指数代码或名称搜索，如 000300 或 沪深300"
                icon={<Search className="w-4 h-4" />}
                onSearch={searchIndexes}
                onSelect={handleSelectIndex}
                pageSize={15}
              />
            </div>

            {/* 当前关注清单（tag 列表） */}
            {watchlistLoading ? (
              <div className="text-sm text-muted-foreground">加载关注清单...</div>
            ) : currentCodes.length === 0 ? (
              <div className="text-sm text-muted-foreground">暂无关注指数</div>
            ) : (
              <div className="flex flex-wrap gap-2 mb-4">
                {(watchlistData?.data?.watchlist ?? []).map((w) => (
                  <span
                    key={w.tsCode}
                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-secondary text-foreground rounded-full text-xs"
                  >
                    {w.name} ({w.tsCode})
                    <button
                      onClick={() => removeCode(w.tsCode)}
                      className="text-muted-foreground hover:text-destructive"
                      aria-label={`移除 ${w.name}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                {/* pending 新增（尚未在后端 watchlist 的） */}
                {(pendingCodes ?? [])
                  .filter((c) => !(watchlistData?.data?.watchlist ?? []).some((w) => w.tsCode === c))
                  .map((c) => (
                    <span
                      key={c}
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-primary-light text-primary rounded-full text-xs"
                    >
                      {c}
                      <button
                        onClick={() => removeCode(c)}
                        className="hover:text-destructive"
                        aria-label={`移除 ${c}`}
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
              </div>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={saveWatchlist}
                disabled={savingWatchlist || pendingCodes === null}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {savingWatchlist ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    保存中...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    保存关注清单（{currentCodes.length} 只）
                  </>
                )}
              </button>
              {pendingCodes !== null && (
                <button
                  onClick={() => setPendingCodes(null)}
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  撤销修改
                </button>
              )}
            </div>

            {watchlistError && (
              <div className="mt-3 flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                {watchlistError}
              </div>
            )}
        </>
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
                  const paramText = record.taskType === 'backfill_index_history'
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
