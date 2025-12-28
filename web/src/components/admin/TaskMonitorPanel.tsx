"use client";

import React, { useState, useEffect } from 'react';
import {
  Clock,
  CheckCircle2,
  XCircle,
  XCircleIcon,
  AlertCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Filter,
  Trash2,
} from 'lucide-react';
import { tasksApi, TaskStatus } from '@/lib/api';
import { useTaskStatus, type TaskData } from '@/hooks/useTaskStatus';

/**
 * 任务状态徽章
 */
function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const config = {
    pending: { color: 'bg-gray-100 text-gray-700', label: '等待中', icon: Clock },
    running: { color: 'bg-blue-100 text-blue-700', label: '运行中', icon: RefreshCw },
    completed: { color: 'bg-green-100 text-green-700', label: '已完成', icon: CheckCircle2 },
    failed: { color: 'bg-red-100 text-red-700', label: '失败', icon: XCircle },
    cancelled: { color: 'bg-yellow-100 text-yellow-700', label: '已取消', icon: XCircleIcon },
  };

  const { color, label, icon: Icon } = config[status];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </span>
  );
}

/**
 * 任务进度条
 */
function TaskProgressBar({ progress, total }: { progress: number; total: number }) {
  const percent = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{progress} / {total}</span>
        <span className="font-medium">{percent}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${
            percent === 100 ? 'bg-green-500' : percent >= 50 ? 'bg-blue-500' : 'bg-blue-400'
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

/**
 * 任务日志组件
 */
interface TaskLogsProps {
  taskId: string | null;
  onClose: () => void;
}

function TaskLogs({ taskId, onClose }: TaskLogsProps) {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (!taskId) return;

    const fetchLogs = async () => {
      setLoading(true);
      try {
        const response = await tasksApi.getTaskLogs(taskId);
        setLogs(response.data?.logs || []);
      } catch (error) {
        console.error('获取日志失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
    // 每5秒刷新日志
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [taskId]);

  if (!taskId) return null;

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-600 bg-red-50';
      case 'WARNING': return 'text-yellow-600 bg-yellow-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-gray-600" />
          <span className="font-medium text-sm">任务日志</span>
          <span className="text-xs text-gray-500">({logs.length} 条)</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            className="p-1 hover:bg-gray-200 rounded"
            title="关闭"
          >
            <XCircle className="w-4 h-4 text-gray-500" />
          </button>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="max-h-64 overflow-y-auto p-4 space-y-2 bg-white">
          {loading ? (
            <div className="text-center text-sm text-gray-500 py-4">加载中...</div>
          ) : logs.length === 0 ? (
            <div className="text-center text-sm text-gray-500 py-4">暂无日志</div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className={`text-xs font-mono p-2 rounded ${getLevelColor(log.level)}`}>
                <div className="flex gap-2">
                  <span className="shrink-0 opacity-60">
                    {new Date(log.createdAt).toLocaleTimeString()}
                  </span>
                  <span className="shrink-0 font-semibold">[{log.level}]</span>
                  <span className="flex-1">{log.message}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/**
 * 任务行组件
 */
interface TaskRowProps {
  task: TaskData;
  onCancel: () => void;
  onViewLogs: () => void;
}

function TaskRow({ task, onCancel, onViewLogs }: TaskRowProps) {
  const [showLogs, setShowLogs] = useState(false);

  // 使用 useTaskStatus Hook 进行实时更新
  const { isPolling } = useTaskStatus(task.taskId, {
    enabled: task.status === 'running' || task.status === 'pending',
    pollInterval: 2000,
  });

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <TaskStatusBadge status={task.status} />
            <span className="text-sm font-mono text-gray-500 truncate">{task.taskId}</span>
            {isPolling && (
              <span className="text-xs text-blue-600 flex items-center gap-1">
                <RefreshCw className="w-3 h-3 animate-spin" />
                更新中
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-900">
            {task.taskType === 'init_sectors' && '初始化板块数据'}
            {task.taskType === 'init_stocks' && '初始化股票数据'}
            {task.taskType === 'init_historical_data' && '初始化历史数据'}
            {task.taskType === 'init_sector_stocks' && '初始化板块成分股'}
            {task.taskType === 'backfill_by_date' && '按日期补齐数据'}
            {task.taskType === 'backfill_by_range' && '按时间段补齐数据'}
          </p>
        </div>

        <div className="flex items-center gap-2 ml-4">
          {(task.status === 'pending' || task.status === 'running') && (
            <button
              onClick={onCancel}
              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="取消任务"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="查看日志"
          >
            <AlertCircle className="w-4 h-4" />
          </button>
        </div>
      </div>

      {(task.status === 'running' || task.status === 'completed') && (
        <div className="mb-3">
          <TaskProgressBar progress={task.progress} total={task.total} />
        </div>
      )}

      {task.errorMessage && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-800 font-medium">错误信息</p>
              <p className="text-sm text-red-700 mt-1">{task.errorMessage}</p>
            </div>
          </div>
        </div>
      )}

      {showLogs && (
        <TaskLogs taskId={task.taskId} onClose={() => setShowLogs(false)} />
      )}

      <div className="flex items-center justify-between text-xs text-gray-500 mt-2 pt-2 border-t border-gray-100">
        <span>创建于: {new Date(task.createdAt).toLocaleString()}</span>
        {task.startedAt && (
          <span>开始: {new Date(task.startedAt).toLocaleString()}</span>
        )}
        {task.completedAt && (
          <span>完成: {new Date(task.completedAt).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
}

/**
 * 任务筛选器
 */
interface TaskFiltersProps {
  status: string;
  taskType: string;
  onStatusChange: (status: string) => void;
  onTaskTypeChange: (taskType: string) => void;
}

function TaskFilters({ status, taskType, onStatusChange, onTaskTypeChange }: TaskFiltersProps) {
  return (
    <div className="flex flex-wrap gap-3 mb-4">
      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-700">筛选:</span>
      </div>

      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">全部状态</option>
        <option value="pending">等待中</option>
        <option value="running">运行中</option>
        <option value="completed">已完成</option>
        <option value="failed">失败</option>
        <option value="cancelled">已取消</option>
      </select>

      <select
        value={taskType}
        onChange={(e) => onTaskTypeChange(e.target.value)}
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">全部类型</option>
        <option value="init_sectors">初始化板块</option>
        <option value="init_stocks">初始化股票</option>
        <option value="init_historical_data">初始化历史数据</option>
        <option value="init_sector_stocks">初始化成分股</option>
        <option value="backfill_by_date">按日期补齐</option>
        <option value="backfill_by_range">按时间段补齐</option>
      </select>
    </div>
  );
}

/**
 * 任务统计卡片
 */
interface TaskStatsProps {
  stats: {
    pending: number;
    running: number;
    completed: number;
    failed: number;
    cancelled: number;
    total: number;
  };
}

function TaskStats({ stats }: TaskStatsProps) {
  const cards = [
    { label: '全部', value: stats.total, color: 'bg-gray-100 text-gray-700' },
    { label: '运行中', value: stats.running, color: 'bg-blue-100 text-blue-700' },
    { label: '已完成', value: stats.completed, color: 'bg-green-100 text-green-700' },
    { label: '失败', value: stats.failed, color: 'bg-red-100 text-red-700' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div key={card.label} className={`${card.color} rounded-lg p-4`}>
          <div className="text-2xl font-bold">{card.value}</div>
          <div className="text-sm opacity-80">{card.label}</div>
        </div>
      ))}
    </div>
  );
}

/**
 * 任务监控主面板
 */
export default function TaskMonitorPanel() {
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [taskTypeFilter, setTaskTypeFilter] = useState('');

  // 获取任务列表
  const fetchTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await tasksApi.listTasks({
        status: statusFilter || undefined,
        task_type: taskTypeFilter || undefined,
        page: 1,
        page_size: 50,
      });
      setTasks(response.data?.tasks || []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  // 获取任务统计
  const fetchStats = async () => {
    try {
      const response = await tasksApi.getTaskStats();
      if (response.data) {
        setStats(response.data);
      }
    } catch (err) {
      console.error('获取统计失败:', err);
    }
  };

  // 初始加载
  useEffect(() => {
    fetchTasks();
    fetchStats();

    // 每5秒刷新
    const interval = setInterval(() => {
      fetchTasks();
      fetchStats();
    }, 5000);

    return () => clearInterval(interval);
  }, [statusFilter, taskTypeFilter]);

  // 取消任务
  const handleCancelTask = async (taskId: string) => {
    if (!confirm('确定要取消此任务吗？')) return;

    try {
      await tasksApi.cancelTask(taskId);
      await fetchTasks();
      await fetchStats();
    } catch (err) {
      alert(`取消任务失败: ${(err as Error).message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">任务监控</h2>
          <p className="text-gray-600 mt-1">查看和管理系统异步任务</p>
        </div>
        <button
          onClick={() => {
            fetchTasks();
            fetchStats();
          }}
          className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          刷新
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <div className="ml-3">
              <h4 className="text-sm font-medium text-red-800">加载失败</h4>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* 任务统计 */}
      {stats && <TaskStats stats={stats} />}

      {/* 筛选器 */}
      <TaskFilters
        status={statusFilter}
        taskType={taskTypeFilter}
        onStatusChange={setStatusFilter}
        onTaskTypeChange={setTaskTypeFilter}
      />

      {/* 任务列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">加载中...</span>
        </div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">暂无任务</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <TaskRow
              key={task.taskId}
              task={task}
              onCancel={() => handleCancelTask(task.taskId)}
              onViewLogs={() => {}}
            />
          ))}
        </div>
      )}
    </div>
  );
}
