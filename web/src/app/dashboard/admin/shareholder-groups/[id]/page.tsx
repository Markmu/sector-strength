'use client';

import { useParams } from 'next/navigation';
import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import ShareholderGroupEditor from '@/components/admin/ShareholderGroupEditor';

/**
 * 编辑股东分组页面（plan-03 重构：弹窗 → 整页表单）
 *
 * 路由：/dashboard/admin/shareholder-groups/[id]
 * 按 id 独立加载详情（GET /api/v1/admin/shareholder-groups/{id}），URL 可刷新/可分享。
 */
export default function EditShareholderGroupPage() {
  const params = useParams();
  const groupId = Number(params.id);

  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader title="编辑分组" subtitle="配置监控组名称与匹配关键词" />
      <ShareholderGroupEditor mode="edit" groupId={groupId} />
    </AdminLayoutWithSidebar>
  );
}
