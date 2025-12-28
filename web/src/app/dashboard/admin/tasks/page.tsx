'use client';

import React from 'react';
import { DashboardLayout, DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import TaskMonitorPanel from '@/components/admin/TaskMonitorPanel';

/**
 * 任务监控页面
 */
export default function TaskMonitorPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="任务监控"
        subtitle="查看和管理系统异步任务"
      />
      <TaskMonitorPanel />
    </AdminLayoutWithSidebar>
  );
}
