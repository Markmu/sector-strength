"use client";

import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Database,
  Calendar,
  CalendarDays,
  AlertTriangle,
  CheckCircle,
  Loader2,
  X,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useRequireAdmin } from '@/hooks/useRequireAdmin';
import { tasksApi } from '@/lib/api';

interface UpdateTask {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  current: number;
  total: number;
  message: string;
  result?: any;
}

interface UpdateRequest {
  task_id: string;
  message: string;
}

interface MissingDatesResponse {
  missing_dates: Record<string, string[]>;
  start_date: string;
  end_date: string;
}

type UpdateMode = 'by-date' | 'by-range';
type TargetType = 'all' | 'all_sectors' | 'sector' | 'stock';

/**
 * 数据更新面板
 *
 * 允许管理员按日期或时间段补齐数据，支持数据覆盖。
 */
export default function DataUpdatePanel() {
  useRequireAdmin();
  const { isAdmin, accessToken } = useAuth();

  // 更新模式
  const [updateMode, setUpdateMode] = useState<UpdateMode>('by-date');

  // 日期设置
  const [selectedDate, setSelectedDate] = useState(formatDate(new Date()));
  const [startDate, setStartDate] = useState(formatDate(daysAgo(7)));
  const [endDate, setEndDate] = useState(formatDate(new Date()));

  // 覆盖选项
  const [overwrite, setOverwrite] = useState(false);
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);

  // 目标选择
  const [targetType, setTargetType] = useState<TargetType>('all');
  const [targetId, setTargetId] = useState('');

  // 任务状态
  const [activeTask, setActiveTask] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Record<string, UpdateTask>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 缺失日期
  const [missingDates, setMissingDates] = useState<MissingDatesResponse | null>(null);
  const [showMissingDates, setShowMissingDates] = useState(false);

  // 轮询任务状态
  useEffect(() => {
    if (!activeTask) {
      return;
    }

    const interval = setInterval(async () => {
      await pollTaskStatus(activeTask);
    }, 2000);

    return () => clearInterval(interval);
  }, [activeTask]);

  const pollTaskStatus = async (taskId: string) => {
    try {
      const response = await tasksApi.getTask(taskId);
      const taskData = response.data;

      if (!taskData) return;

      setTasks(prev => ({
        ...prev,
        [taskId]: {
          task_id: taskData.taskId,
          status: taskData.status as UpdateTask['status'],
          current: taskData.progress,
          total: taskData.total,
          message: taskData.errorMessage || '处理中'
        }
      }));

      if (taskData.status === 'completed' || taskData.status === 'failed' || taskData.status === 'cancelled') {
        setActiveTask(null);
        setLoading(false);
      }
    } catch (error) {
      console.error('轮询任务状态失败:', error);
    }
  };

  const startUpdate = async () => {
    try {
      setLoading(true);
      setError(null);

      // 验证覆盖选项
      if (overwrite && !confirmOverwrite) {
        setError('请确认覆盖操作');
        setLoading(false);
        return;
      }

      // 映射到新的任务类型
      const taskType = updateMode === 'by-date' ? 'backfill_by_date' : 'backfill_by_range';

      // 构建参数
      const params = updateMode === 'by-date'
        ? {
            target_date: selectedDate,
            overwrite,
            target_type: targetType === 'all' ? undefined : (targetType === 'all_sectors' ? 'sector' : targetType),
            target_id: (targetType !== 'all' && targetType !== 'all_sectors') ? targetId : undefined
          }
        : {
            start_date: startDate,
            end_date: endDate,
            overwrite,
            target_type: targetType === 'all' ? undefined : (targetType === 'all_sectors' ? 'sector' : targetType),
            target_id: (targetType !== 'all' && targetType !== 'all_sectors') ? targetId : undefined
          };

      // 使用新的 tasks API 创建任务
      const response = await tasksApi.createTask({
        task_type: taskType,
        params,
        max_retries: 3,
        timeout_seconds: 7200
      });

      if (!response.data?.taskId) {
        throw new Error('创建任务失败：未返回任务ID');
      }

      const taskId = response.data.taskId;
      setActiveTask(taskId);
      setTasks(prev => ({
        ...prev,
        [taskId]: {
          task_id: taskId,
          status: 'pending',
          current: 0,
          total: 0,
          message: `已创建${updateMode === 'by-date' ? '按日期' : '按时间段'}补齐任务`
        }
      }));

      // 重置覆盖确认
      setConfirmOverwrite(false);
    } catch (error) {
      console.error('更新失败:', error);
      setError((error as Error).message);
      setLoading(false);
    }
  };

  const fetchMissingDates = async () => {
    try {
      setShowMissingDates(true);
      setLoading(true);

      const params = new URLSearchParams();
      if (targetType === 'stock' && targetId) {
        params.append('stock_symbol', targetId);
      }
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await fetch(
        `/api/v1/admin/update/missing-dates?${params}`,
        {
          headers: { 'Authorization': `Bearer ${accessToken}` }
        }
      );

      if (response.ok) {
        const result = await response.json();
        setMissingDates(result.data);
      } else {
        throw new Error('查询缺失日期失败');
      }
    } catch (error) {
      console.error('查询缺失日期失败:', error);
      setError((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const cancelTask = async (taskId: string) => {
    try {
      await tasksApi.cancelTask(taskId);
      setTasks(prev => ({
        ...prev,
        [taskId]: { ...prev[taskId], status: 'cancelled' as const, message: '任务已取消' }
      }));
      setActiveTask(null);
      setLoading(false);
    } catch (error) {
      console.error('取消任务失败:', error);
    }
  };

  const getProgress = (task: UpdateTask) => {
    if (task.total === 0) return 0;
    return Math.round((task.current / task.total) * 100);
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      pending: 'bg-gray-100 text-gray-700',
      running: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
      cancelled: 'bg-yellow-100 text-yellow-700'
    };

    const labels = {
      pending: '等待中',
      running: '进行中',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status as keyof typeof styles]}`}>
        {labels[status as keyof typeof labels]}
      </span>
    );
  };

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-600">您没有权限访问此页面</p>
        </div>
      </div>
    );
  }

  const totalMissing = Object.values(missingDates?.missing_dates || {})
    .reduce((sum, dates) => sum + (dates?.length || 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">数据更新</h2>
        <p className="text-gray-600">
          按日期或时间段补齐数据，支持数据覆盖功能。
        </p>
      </div>

      {/* 更新模式选择 */}
      <div className="flex gap-2">
        <button
          onClick={() => setUpdateMode('by-date')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
            updateMode === 'by-date'
              ? 'bg-blue-50 border-blue-300 text-blue-700'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>按日期补齐</span>
        </button>
        <button
          onClick={() => setUpdateMode('by-range')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
            updateMode === 'by-range'
              ? 'bg-blue-50 border-blue-300 text-blue-700'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }`}
        >
          <CalendarDays className="w-4 h-4" />
          <span>按时间段补齐</span>
        </button>
      </div>

      {/* 日期设置 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {updateMode === 'by-date' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              选择日期
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              max={formatDate(new Date())}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                开始日期
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                max={endDate}
                disabled={loading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                结束日期
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                min={startDate}
                max={formatDate(new Date())}
                disabled={loading}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
              />
            </div>
          </div>
        )}
      </div>

      {/* 目标选择 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          更新范围
        </label>
        <div className="flex flex-wrap gap-2 mb-3">
          {(['all', 'all_sectors', 'sector', 'stock'] as TargetType[]).map((type) => (
            <button
              key={type}
              onClick={() => setTargetType(type)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                targetType === type
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-200 hover:bg-gray-50'
              }`}
            >
              {type === 'all' ? '全部股票' : type === 'all_sectors' ? '全部板块' : type === 'sector' ? '指定板块' : '指定股票'}
            </button>
          ))}
        </div>
        {targetType !== 'all' && targetType !== 'all_sectors' && (
          <input
            type="text"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            placeholder={targetType === 'sector' ? '板块代码 (如: industry)' : '股票代码 (如: 000001)'}
            disabled={loading}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
          />
        )}
      </div>

      {/* 覆盖选项 */}
      <div className={`bg-white rounded-lg shadow-sm border p-6 ${
        overwrite ? 'border-orange-200 bg-orange-50' : 'border-gray-200'
      }`}>
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="overwrite"
            checked={overwrite}
            onChange={(e) => {
              setOverwrite(e.target.checked);
              if (e.target.checked) {
                setConfirmOverwrite(false);
              }
            }}
            disabled={loading}
            className="mt-1"
          />
          <div className="flex-1">
            <label htmlFor="overwrite" className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
              <AlertTriangle className={`w-4 h-4 ${overwrite ? 'text-orange-600' : 'text-gray-400'}`} />
              覆盖已有数据
            </label>
            <p className="mt-1 text-sm text-gray-600">
              {overwrite
                ? '将强制更新已有数据，用于修正异常数据。此操作不可撤销。'
                : '只添加缺失的数据，不修改已有数据。'}
            </p>
            {overwrite && (
              <div className="mt-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={confirmOverwrite}
                    onChange={(e) => setConfirmOverwrite(e.target.checked)}
                    disabled={loading}
                    className="text-orange-600"
                  />
                  <span className="text-orange-700 font-medium">
                    我确认要覆盖已有数据
                  </span>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={startUpdate}
          disabled={loading || (overwrite && !confirmOverwrite)}
          className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Database className="w-5 h-5" />
          <span className="font-medium">
            {updateMode === 'by-date' ? '按日期补齐' : '按时间段补齐'}
          </span>
        </button>

        <button
          onClick={fetchMissingDates}
          disabled={loading}
          className="flex items-center gap-2 px-6 py-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <CalendarDays className="w-5 h-5 text-gray-600" />
          <span className="font-medium">查询缺失日期</span>
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-red-600" />
            </div>
            <div className="ml-3 flex-1">
              <h4 className="text-sm font-medium text-red-800">操作失败</h4>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-3 text-red-600 hover:text-red-800"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* 活动任务 */}
      {activeTask && tasks[activeTask] && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              <h3 className="text-lg font-semibold">正在进行</h3>
              {getStatusBadge(tasks[activeTask].status)}
            </div>
            <button
              onClick={() => cancelTask(activeTask)}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              title="取消任务"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">{tasks[activeTask].message}</span>
              <span className="font-medium">{tasks[activeTask].current} / {tasks[activeTask].total}</span>
            </div>

            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${getProgress(tasks[activeTask])}%` }}
              />
            </div>

            <div className="text-right text-sm text-gray-500">
              {getProgress(tasks[activeTask])}%
            </div>
          </div>
        </div>
      )}

      {/* 缺失日期 */}
      {showMissingDates && missingDates && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold">缺失日期查询结果</h3>
            <button
              onClick={() => setShowMissingDates(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="px-6 py-4">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-sm text-gray-700">
                共发现 <span className="font-bold">{Object.keys(missingDates.missing_dates).length}</span> 只股票
                有 <span className="font-bold">{totalMissing}</span> 个缺失日期
              </span>
            </div>
            {totalMissing > 0 && (
              <div className="max-h-60 overflow-y-auto">
                {Object.entries(missingDates.missing_dates).slice(0, 20).map(([symbol, dates]) => (
                  <div key={symbol} className="py-2 border-b border-gray-100 last:border-0">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{symbol}</span>
                      <span className="text-sm text-gray-500">{dates.length} 个缺失</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {dates.slice(0, 5).join(', ')}
                      {dates.length > 5 && '...'}
                    </div>
                  </div>
                ))}
                {Object.keys(missingDates.missing_dates).length > 20 && (
                  <div className="text-center text-sm text-gray-500 py-2">
                    还有 {Object.keys(missingDates.missing_dates).length - 20} 只股票未显示
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 提示信息 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-yellow-800">注意事项</h4>
            <div className="mt-1 text-sm text-yellow-700">
              <ul className="list-disc list-inside space-y-1">
                <li>按日期补齐：适合每日收盘后更新当天数据</li>
                <li>按时间段补齐：适合补齐历史缺失数据</li>
                <li>数据覆盖会修改已有数据，请谨慎使用</li>
                <li>更新过程中可以随时取消任务</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 辅助函数
function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

function daysAgo(days: number): Date {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date;
}
