"use client";

import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  TrendingUp,
  Calendar,
  CalendarDays,
  AlertTriangle,
  CheckCircle,
  Loader2,
  X,
  AlertCircle,
  LineChart,
  History
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useRequireAdmin } from '@/hooks/useRequireAdmin';
import { tasksApi } from '@/lib/api';
import SectorSearchSelect from './SectorSearchSelect';

interface UpdateTask {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  current: number;
  total: number;
  message: string;
  result?: any;
}

type CalculationMode = 'by-date' | 'by-range' | 'full-history';
type TargetType = 'all' | 'single';

/**
 * 板块强度计算面板
 *
 * 允许管理员计算或更新板块强度得分数据。
 */
export default function SectorStrengthCalculationPanel() {
  useRequireAdmin();
  const { isAdmin, accessToken } = useAuth();

  // 计算模式
  const [calculationMode, setCalculationMode] = useState<CalculationMode>('by-range');

  // 日期设置
  const [selectedDate, setSelectedDate] = useState(formatDate(new Date()));
  const [startDate, setStartDate] = useState(formatDate(daysAgo(60)));
  const [endDate, setEndDate] = useState(formatDate(new Date()));

  // 覆盖选项
  const [overwrite, setOverwrite] = useState(false);
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);

  // 目标选择
  const [targetType, setTargetType] = useState<TargetType>('all');
  const [sectorId, setSectorId] = useState<number | null>(null);

  // 任务状态
  const [activeTask, setActiveTask] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Record<string, UpdateTask>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const startCalculation = async () => {
    try {
      setLoading(true);
      setError(null);

      // 验证覆盖选项
      if (overwrite && !confirmOverwrite) {
        setError('请确认覆盖操作');
        setLoading(false);
        return;
      }

      // 验证目标选择（按时间段计算需要）
      if (calculationMode === 'by-range' && targetType === 'single' && !sectorId) {
        setError('请选择板块');
        setLoading(false);
        return;
      }

      // 验证目标选择（完整历史计算需要）
      if (calculationMode === 'full-history' && targetType === 'single' && !sectorId) {
        setError('请选择板块');
        setLoading(false);
        return;
      }

      // 映射到任务类型
      let taskType: string;
      let params: any;

      if (calculationMode === 'by-date') {
        taskType = 'calculate_sector_strength_by_date';
        params = {
          target_date: selectedDate,
          overwrite
        };
      } else if (calculationMode === 'by-range') {
        taskType = 'calculate_sector_strength_by_range';
        params = {
          start_date: startDate,
          end_date: endDate,
          overwrite,
          sector_id: targetType === 'single' ? String(sectorId) : undefined
        };
      } else {
        // full-history
        taskType = 'calculate_sector_strength_full_history';
        params = {
          overwrite,
          sector_id: targetType === 'single' ? String(sectorId) : undefined
        };
      }

      // 使用 tasks API 创建任务
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
          message: `已创建${calculationMode === 'by-date' ? '按日期' : calculationMode === 'by-range' ? '按时间段' : '完整历史'}板块强度计算任务`
        }
      }));

      // 重置覆盖确认
      setConfirmOverwrite(false);
    } catch (error) {
      console.error('计算失败:', error);
      setError((error as Error).message);
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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">板块强度计算</h2>
        <p className="text-gray-600">
          计算或更新板块强度得分，支持多种日期范围和计算模式。
        </p>
      </div>

      {/* 计算模式选择 */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setCalculationMode('by-date')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
            calculationMode === 'by-date'
              ? 'bg-blue-50 border-blue-300 text-blue-700'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>按日期计算</span>
        </button>
        <button
          onClick={() => setCalculationMode('by-range')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
            calculationMode === 'by-range'
              ? 'bg-blue-50 border-blue-300 text-blue-700'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }`}
        >
          <CalendarDays className="w-4 h-4" />
          <span>按时间段计算</span>
        </button>
        <button
          onClick={() => setCalculationMode('full-history')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
            calculationMode === 'full-history'
              ? 'bg-blue-50 border-blue-300 text-blue-700'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }`}
        >
          <History className="w-4 h-4" />
          <span>完整历史计算</span>
        </button>
      </div>

      {/* 日期设置 */}
      {calculationMode !== 'full-history' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {calculationMode === 'by-date' ? (
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
      )}

      {/* 完整历史计算说明 */}
      {calculationMode === 'full-history' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <History className="w-5 h-5 text-green-600" />
            </div>
            <div className="ml-3">
              <h4 className="text-sm font-medium text-green-800">完整历史计算模式</h4>
              <div className="mt-1 text-sm text-green-700">
                <p>此模式将自动从每个板块的最早数据日期开始，逐步计算到最新数据的所有强度得分。</p>
                <p className="mt-1">无需手动选择日期范围，系统会自动计算所有可用历史数据。</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 目标选择 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          计算范围
        </label>
        <div className="flex flex-wrap gap-2 mb-3">
          {(['all', 'single'] as TargetType[]).map((type) => (
            <button
              key={type}
              onClick={() => setTargetType(type)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                targetType === type
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-200 hover:bg-gray-50'
              }`}
            >
              {type === 'all' ? '全部板块' : '指定板块'}
            </button>
          ))}
        </div>
        {targetType === 'single' && (
          <SectorSearchSelect
            value={sectorId}
            onChange={setSectorId}
            disabled={loading}
            placeholder="搜索板块名称或代码..."
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
            id="overwrite-strength"
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
            <label htmlFor="overwrite-strength" className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
              <AlertTriangle className={`w-4 h-4 ${overwrite ? 'text-orange-600' : 'text-gray-400'}`} />
              覆盖已有强度数据
            </label>
            <p className="mt-1 text-sm text-gray-600">
              {overwrite
                ? '将强制更新已有强度数据，用于修正异常计算结果。此操作不可撤销。'
                : '只添加缺失的强度数据，不修改已有数据。'}
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
                    我确认要覆盖已有强度数据
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
          onClick={startCalculation}
          disabled={loading || (overwrite && !confirmOverwrite) ||
            (targetType === 'single' && !sectorId)}
          className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <TrendingUp className="w-5 h-5" />
          <span className="font-medium">
            {calculationMode === 'by-date' ? '按日期计算' :
             calculationMode === 'by-range' ? '按时间段计算' :
             '开始完整历史计算'}
          </span>
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

      {/* 提示信息 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <LineChart className="w-5 h-5 text-blue-600" />
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-800">功能说明</h4>
            <div className="mt-1 text-sm text-blue-700">
              <ul className="list-disc list-inside space-y-1">
                <li>按日期计算：补齐指定日期的板块强度数据</li>
                <li>按时间段计算：计算指定时间段内的板块强度，支持筛选特定板块</li>
                <li>完整历史计算：从板块最早数据日期自动计算到最新日期的完整强度历史</li>
                <li>强度得分基于多周期均线综合计算，范围 0-100</li>
                <li>数据覆盖会重新计算并更新已有数据，请谨慎使用</li>
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
