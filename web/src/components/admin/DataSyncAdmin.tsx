'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardBody } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { adminApi } from '@/lib/api';
import {
  RefreshCw,
  Play,
  Square,
  Clock,
  Database,
  Server,
  Trash2,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

// 类型定义
interface UpdateStatus {
  success: boolean;
  started_at?: string;
  completed_at?: string;
  sectors_updated?: number;
  stocks_updated?: number;
  error?: string;
}

interface UpdateHistoryItem {
  id: string;
  started_at: string;
  completed_at?: string;
  status: 'success' | 'failed' | 'running';
  sectors_updated?: number;
  stocks_updated?: number;
  error?: string;
}

interface SchedulerStatus {
  is_running: boolean;
  jobs: {
    [key: string]: {
      id: string;
      name: string;
      next_run_time?: string;
    };
  };
}

interface SystemHealth {
  status: string;
  database: string;
  scheduler: string;
  cache: string;
}

/**
 * 管理员数据同步管理页面
 * 提供数据更新、调度器管理、缓存管理和系统健康检查功能
 */
export const DataSyncAdmin: React.FC = () => {
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus | null>(null);
  const [updateHistory, setUpdateHistory] = useState<UpdateHistoryItem[]>([]);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [cacheStats, setCacheStats] = useState<any>(null);
  const [dataQuality, setDataQuality] = useState<any>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 加载所有数据
  const loadAllData = useCallback(async () => {
    try {
      setRefreshing(true);
      const [statusRes, historyRes, schedulerRes, healthRes, cacheRes, qualityRes] =
        await Promise.all([
          adminApi.getUpdateStatus(),
          adminApi.getUpdateHistory({ page: 1, page_size: 10 }),
          adminApi.getSchedulerStatus(),
          adminApi.getSystemHealth(),
          adminApi.getCacheStats(),
          adminApi.checkDataQuality(),
        ]);

      if (statusRes.data) setUpdateStatus(statusRes.data);
      if (historyRes.data?.items) setUpdateHistory(historyRes.data.items);
      if (schedulerRes.data) setSchedulerStatus(schedulerRes.data);
      if (healthRes.data) setSystemHealth(healthRes.data);
      if (cacheRes.data) setCacheStats(cacheRes.data);
      if (qualityRes.data) setDataQuality(qualityRes.data);
    } catch (error: any) {
      console.error('加载数据失败:', error);
      showMessage('error', error.message || '加载数据失败');
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  // 触发数据更新
  const handleTriggerUpdate = async () => {
    setIsLoading(true);
    try {
      const response = await adminApi.triggerUpdate();
      if (response.data) {
        showMessage('success', `数据更新已触发，任务ID: ${response.data.task_id}`);
        await loadAllData();
      }
    } catch (error: any) {
      showMessage('error', error.message || '触发更新失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 启动调度器
  const handleStartScheduler = async () => {
    try {
      await adminApi.startScheduler();
      showMessage('success', '调度器已启动');
      await loadAllData();
    } catch (error: any) {
      showMessage('error', error.message || '启动调度器失败');
    }
  };

  // 停止调度器
  const handleStopScheduler = async () => {
    try {
      await adminApi.stopScheduler();
      showMessage('success', '调度器已停止');
      await loadAllData();
    } catch (error: any) {
      showMessage('error', error.message || '停止调度器失败');
    }
  };

  // 清除缓存
  const handleClearCache = async (pattern?: string) => {
    try {
      const response = await adminApi.clearCache(pattern);
      if (response.data) {
        showMessage('success', response.data.message || '缓存已清除');
        await loadAllData();
      }
    } catch (error: any) {
      showMessage('error', error.message || '清除缓存失败');
    }
  };

  // 触发特定任务
  const handleTriggerJob = async (jobId: string) => {
    try {
      await adminApi.triggerJob(jobId);
      showMessage('success', `任务 ${jobId} 已触发`);
      await loadAllData();
    } catch (error: any) {
      showMessage('error', error.message || '触发任务失败');
    }
  };

  // 格式化时间
  const formatTime = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div className="space-y-6">
      {/* 消息提示 */}
      {message && (
        <div
          className={`p-4 rounded-lg flex items-center gap-2 ${
            message.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <XCircle className="w-5 h-5" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* 系统健康状态 */}
      <Card>
        <CardBody className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Server className="w-5 h-5" />
              系统健康状态
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadAllData}
              disabled={refreshing}
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
          {systemHealth && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className={`text-2xl font-bold ${
                  systemHealth.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {systemHealth.status === 'healthy' ? '正常' : '异常'}
                </div>
                <div className="text-sm text-gray-500">整体状态</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className={`text-2xl font-bold ${
                  systemHealth.database === 'connected' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {systemHealth.database === 'connected' ? '已连接' : '未连接'}
                </div>
                <div className="text-sm text-gray-500">数据库</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className={`text-2xl font-bold ${
                  schedulerStatus?.is_running ? 'text-green-600' : 'text-yellow-600'
                }`}>
                  {schedulerStatus?.is_running ? '运行中' : '已停止'}
                </div>
                <div className="text-sm text-gray-500">调度器</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {systemHealth.cache === 'active' ? '活跃' : '未激活'}
                </div>
                <div className="text-sm text-gray-500">缓存</div>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* 数据更新管理 */}
      <Card>
        <CardBody className="p-6">
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Database className="w-5 h-5" />
            数据更新管理
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Button
              onClick={handleTriggerUpdate}
              disabled={isLoading}
              className="w-full"
            >
              <Play className="w-4 h-4 mr-2" />
              手动触发数据更新
            </Button>
            <Button
              onClick={() => handleClearCache()}
              variant="outline"
              className="w-full"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              清除所有缓存
            </Button>
          </div>

          {/* 最新更新状态 */}
          {updateStatus && (
            <div className="p-4 bg-gray-50 rounded-lg mb-4">
              <h4 className="font-medium mb-2">最新更新状态</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-500">开始时间:</span>{' '}
                  {formatTime(updateStatus.started_at)}
                </div>
                <div>
                  <span className="text-gray-500">完成时间:</span>{' '}
                  {formatTime(updateStatus.completed_at)}
                </div>
                <div>
                  <span className="text-gray-500">板块更新:</span>{' '}
                  {updateStatus.sectors_updated || 0}
                </div>
                <div>
                  <span className="text-gray-500">股票更新:</span>{' '}
                  {updateStatus.stocks_updated || 0}
                </div>
                {updateStatus.error && (
                  <div className="col-span-2 text-red-600">
                    <span className="text-gray-500">错误:</span> {updateStatus.error}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 更新历史 */}
          <div>
            <h4 className="font-medium mb-2">更新历史 (最近10条)</h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {updateHistory.length > 0 ? (
                updateHistory.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 bg-white border border-gray-200 rounded-lg flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      {item.status === 'success' ? (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      ) : item.status === 'failed' ? (
                        <XCircle className="w-4 h-4 text-red-600" />
                      ) : (
                        <Clock className="w-4 h-4 text-yellow-600" />
                      )}
                      <span className="text-sm">{formatTime(item.started_at)}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {item.sectors_updated || 0} 板块 / {item.stocks_updated || 0} 股票
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-4">暂无更新历史</div>
              )}
            </div>
          </div>
        </CardBody>
      </Card>

      {/* 调度器管理 */}
      <Card>
        <CardBody className="p-6">
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5" />
            调度器管理
          </h3>

          <div className="flex gap-4 mb-6">
            <Button
              onClick={handleStartScheduler}
              disabled={schedulerStatus?.is_running}
              variant={schedulerStatus?.is_running ? 'outline' : 'primary'}
            >
              <Play className="w-4 h-4 mr-2" />
              启动调度器
            </Button>
            <Button
              onClick={handleStopScheduler}
              disabled={!schedulerStatus?.is_running}
              variant="outline"
            >
              <Square className="w-4 h-4 mr-2" />
              停止调度器
            </Button>
          </div>

          {/* 定时任务列表 */}
          {schedulerStatus?.jobs && (
            <div>
              <h4 className="font-medium mb-2">定时任务</h4>
              <div className="space-y-2">
                {Object.entries(schedulerStatus.jobs).map(([key, job]) => (
                  <div
                    key={key}
                    className="p-3 bg-gray-50 rounded-lg flex items-center justify-between"
                  >
                    <div>
                      <div className="font-medium">{job.name || key}</div>
                      <div className="text-sm text-gray-500">
                        下次运行: {formatTime(job.next_run_time)}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleTriggerJob(key)}
                    >
                      <Play className="w-3 h-3 mr-1" />
                      立即执行
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* 缓存管理 */}
      <Card>
        <CardBody className="p-6">
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Database className="w-5 h-5" />
            缓存管理
          </h3>

          {cacheStats && (
            <div className="p-4 bg-gray-50 rounded-lg mb-4">
              <div className="text-sm">
                <div>
                  <span className="text-gray-500">后端:</span> {cacheStats.backend}
                </div>
                <div>
                  <span className="text-gray-500">前缀:</span> {cacheStats.prefix}
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => handleClearCache()} variant="outline" size="sm">
              清除所有缓存
            </Button>
            <Button
              onClick={() => handleClearCache('sectors')}
              variant="outline"
              size="sm"
            >
              清除板块缓存
            </Button>
            <Button
              onClick={() => handleClearCache('stocks')}
              variant="outline"
              size="sm"
            >
              清除股票缓存
            </Button>
            <Button
              onClick={() => handleClearCache('strength')}
              variant="outline"
              size="sm"
            >
              清除强度缓存
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* 数据质量 */}
      {dataQuality && (
        <Card>
          <CardBody className="p-6">
            <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5" />
              数据质量检查
            </h3>

            {dataQuality.integrity?.has_issues ? (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center gap-2 text-yellow-700 font-medium mb-2">
                  <AlertTriangle className="w-5 h-5" />
                  发现数据问题
                </div>
                <ul className="list-disc list-inside text-sm text-yellow-700">
                  {dataQuality.integrity.issues?.map((issue: string, idx: number) => (
                    <li key={idx}>{issue}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
                <CheckCircle className="w-5 h-5" />
                数据质量正常，未发现问题
              </div>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
};

export default DataSyncAdmin;
