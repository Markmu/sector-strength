'use client';

import React from 'react';
import { DashboardLayout, DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import UserManagementPanel from '@/components/admin/UserManagementPanel';

/**
 * 用户管理页面
 */
export default function UserManagementPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="用户管理"
        subtitle="管理用户账户、角色和权限"
      />
      <UserManagementPanel />
    </AdminLayoutWithSidebar>
  );
}
