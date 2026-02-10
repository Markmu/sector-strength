"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { ShieldAlert, Database, TrendingUp, List, Play, X, Loader2, AlertCircle, Calendar, BarChart3 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useRequireAdmin } from '@/hooks/useRequireAdmin';
import { tasksApi, TaskStatus } from '@/lib/api';

interface InitTask {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  current: number;
  total: number;
  message: string;
  result?: any;
}

/**
 * 数据初始化面板
 *
 * 允许管理员从 AkShare 初始化板块、股票和历史数据。
 */
export default function DataInitPanel() {
  useRequireAdmin();
  const { isAdmin, isAuthenticated, accessToken } = useAuth();
  // 默认设置为过去 60 天
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 60);
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [activeTask, setActiveTask] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Record<string, InitTask>>({});
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
          status: taskData.status as InitTask['status'],
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

  const startInit = async (type: 'sectors' | 'stocks' | 'historical' | 'sector_historical' | 'sector_classification' | 'all') => {
    try {
      setLoading(true);
      setError(null);

      // 映射到新的任务类型
      const taskTypeMap = {
        sectors: 'init_sectors',
        stocks: 'init_stocks',
        historical: 'init_historical_data',
        sector_historical: 'init_sector_historical_data',
        sector_classification: 'init_sector_classifications',
        all: 'init_stocks'  // 全部初始化默认为初始化股票（最常用）
      };

      // 映射参数 - 使用日期范围
      const params = (type === 'historical' || type === 'sector_historical' || type === 'sector_classification') ? {
        start_date: startDate,
        end_date: endDate
      } : undefined;

      // 使用新的 tasks API 创建任务
      const response = await tasksApi.createTask({
        task_type: taskTypeMap[type],
        params,
        max_retries: 3,
        timeout_seconds: 3600
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
          message: `已创建${type === 'all' ? '完整' : ''}初始化任务`
        }
      }));
    } catch (error) {
      console.error('初始化失败:', error);
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

  const getProgress = (task: InitTask) => {
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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">数据初始化</h2>
        <p className="text-gray-600">
          从 AkShare 拉取板块、股票和历史数据，初始化系统数据库。
        </p>
      </div>

      {/* 日期范围设置 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-blue-600" />
          <label className="text-sm font-medium text-gray-700">
            历史数据日期范围
          </label>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 开始日期 */}
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-2">
              开始日期
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={loading}
              max={endDate}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
          </div>

          {/* 结束日期 */}
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-2">
              结束日期
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={loading}
              min={startDate}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        {/* 快捷选择 */}
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-gray-500">快捷选择：</span>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setDate(start.getDate() - 30);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 30 天
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setDate(start.getDate() - 60);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 60 天
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setDate(start.getDate() - 90);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 90 天
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setDate(start.getDate() - 180);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近半年
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setFullYear(start.getFullYear() - 1);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 1 年
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setFullYear(start.getFullYear() - 2);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 2 年
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setFullYear(start.getFullYear() - 3);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 3 年
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setFullYear(start.getFullYear() - 5);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 5 年
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setFullYear(start.getFullYear() - 10);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 10 年
          </button>
          <button
            onClick={() => {
              const end = new Date();
              const start = new Date();
              start.setFullYear(start.getFullYear() - 20);
              setStartDate(start.toISOString().split('T')[0]);
              setEndDate(end.toISOString().split('T')[0]);
            }}
            disabled={loading}
            className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-md transition-colors disabled:opacity-50"
          >
            最近 20 年
          </button>
        </div>

        {/* 日期范围提示 */}
        <div className="mt-3 text-sm text-gray-500">
          将获取 <span className="font-medium text-gray-700">{startDate}</span>
          至 <span className="font-medium text-gray-700">{endDate}</span>
          的历史数据
        </div>
      </div>

      {/* 初始化按钮 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
        <button
          onClick={() => startInit('sectors')}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Database className="w-5 h-5 text-blue-600" />
          <span className="font-medium">初始化板块</span>
        </button>

        <button
          onClick={() => startInit('stocks')}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <List className="w-5 h-5 text-green-600" />
          <span className="font-medium">初始化股票</span>
        </button>

        <button
          onClick={() => startInit('sector_historical')}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <BarChart3 className="w-5 h-5 text-indigo-600" />
          <span className="font-medium">板块历史数据</span>
        </button>

        <button
          onClick={() => startInit('historical')}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-blue-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <TrendingUp className="w-5 h-5 text-purple-600" />
          <span className="font-medium">股票历史数据</span>
        </button>

        <button
          onClick={() => startInit('sector_classification')}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-orange-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <BarChart3 className="w-5 h-5 text-orange-600" />
          <span className="font-medium">板块分类初始化</span>
        </button>

        <button
          onClick={() => startInit('all')}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="w-5 h-5" />
          <span className="font-medium">全部初始化</span>
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

      {/* 任务历史 */}
      {Object.keys(tasks).length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold">任务历史</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {Object.values(tasks).reverse().map((task) => (
              <div key={task.task_id} className="px-6 py-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    {getStatusBadge(task.status)}
                    <span className="text-sm text-gray-600">{task.message}</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {task.current} / {task.total}
                  </span>
                </div>

                {task.result && (
                  <div className="mt-2 p-3 bg-gray-50 rounded text-sm">
                    <pre className="text-xs overflow-auto max-h-40">
                      {JSON.stringify(task.result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 提示信息 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <ShieldAlert className="w-5 h-5 text-yellow-600" />
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-yellow-800">注意事项</h4>
            <div className="mt-1 text-sm text-yellow-700">
              <ul className="list-disc list-inside space-y-1">
                <li>数据初始化可能需要较长时间，取决于数据量和网络状况</li>
                <li>请确保网络连接稳定，AkShare API 有请求频率限制</li>
                <li>建议先初始化板块，再初始化股票，最后初始化历史数据</li>
                <li>历史数据越多，初始化时间越长（100 只股票约需 5-10 分钟）</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
