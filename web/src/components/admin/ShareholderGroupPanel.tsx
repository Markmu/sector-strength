'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Loader2, AlertCircle } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
} from '@/components/ui/alert-dialog';
import Button from '@/components/ui/Button';
import { adminApi, type ShareholderGroupListItem } from '@/lib/api';

const BASE_PATH = '/dashboard/admin/shareholder-groups';

/**
 * 股东分组管理面板（plan-03）
 *
 * 功能：
 *  - 分组列表表格（组名 / 描述 / 匹配规则数 / 匹配股数 / 操作）
 *  - 新增 / 编辑：跳转独立整页表单（/new 与 /[id]），见 ShareholderGroupEditor
 *  - 删除分组（AlertDialog 二次确认）
 *  - API 失败 inline 错误提示
 *
 * 数据来源：plan-01 后端 Admin API /api/v1/admin/shareholder-groups
 * （响应外层 { success, data, message }，由 AdminApiClient.request 提取 data）
 */
export default function ShareholderGroupPanel() {
  const router = useRouter();
  const [groups, setGroups] = useState<ShareholderGroupListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [listError, setListError] = useState<string | null>(null);

  // 删除确认 AlertDialog 状态
  const [deleting, setDeleting] = useState<ShareholderGroupListItem | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // 刷新分组列表
  const fetchGroups = useCallback(async () => {
    setLoading(true);
    setListError(null);
    try {
      const res = await adminApi.getShareholderGroups();
      setGroups((res.data as ShareholderGroupListItem[]) ?? []);
    } catch (err) {
      setListError((err as Error).message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始加载：用 ref 防止 React StrictMode 在 dev 下对 useEffect 的双重调用导致
  // 重复请求（生产环境 StrictMode 不双重调用，ref 不影响）。显式 refresh（fetchGroups）
  // 由用户操作（删除）触发，不受此 ref 影响。
  const initialFetchedRef = useRef(false);
  useEffect(() => {
    if (initialFetchedRef.current) return;
    initialFetchedRef.current = true;
    fetchGroups();
  }, [fetchGroups]);

  const handleOpenCreate = () => {
    router.push(`${BASE_PATH}/new`);
  };

  const handleOpenEdit = (group: ShareholderGroupListItem) => {
    router.push(`${BASE_PATH}/${group.id}`);
  };

  const handleConfirmDelete = async () => {
    if (!deleting) return;
    setDeleteError(null);
    try {
      await adminApi.deleteShareholderGroup(deleting.id);
      setDeleting(null);
      await fetchGroups();
    } catch (err) {
      setDeleteError((err as Error).message || '删除失败');
    }
  };

  const handleCancelDelete = () => {
    setDeleting(null);
    setDeleteError(null);
  };

  return (
    <div className="space-y-4">
      {/* 顶部操作栏 */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          管理股东监控组及其匹配关键词规则。
        </p>
        <Button onClick={handleOpenCreate} icon={<Plus className="w-4 h-4" />}>
          新增分组
        </Button>
      </div>

      {/* 列表加载失败提示（TC-1.11） */}
      {listError && (
        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-destructive">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>加载失败：{listError}</span>
        </div>
      )}

      {/* 分组列表表格 */}
      <div className="w-full overflow-auto rounded-xl border border-border bg-card">
        <table className="w-full text-base">
          <thead className="bg-background border-b border-border">
            <tr>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left border-r border-border">
                分组名称
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left border-r border-border">
                描述
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left border-r border-border">
                匹配规则数
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left border-r border-border">
                匹配股数
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  <div className="flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    加载中...
                  </div>
                </td>
              </tr>
            ) : groups.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  暂无分组
                </td>
              </tr>
            ) : (
              groups.map((group) => (
                <tr key={group.id} className="hover:bg-background/80 transition-colors">
                  <td className="px-4 py-3 text-foreground border-r border-secondary">
                    <span className="font-medium">{group.name}</span>
                    {group.isSystem && (
                      <span className="ml-2 text-xs text-muted-foreground">系统预定义</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-foreground border-r border-secondary">
                    {group.description || '-'}
                  </td>
                  <td className="px-4 py-3 text-foreground border-r border-secondary">
                    {group.ruleCount}
                  </td>
                  <td className="px-4 py-3 text-foreground border-r border-secondary">
                    {group.matchedStockCount}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleOpenEdit(group)}
                      >
                        编辑
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => {
                          setDeleting(group);
                          setDeleteError(null);
                        }}
                      >
                        删除
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 删除确认 AlertDialog */}
      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && handleCancelDelete()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除分组</AlertDialogTitle>
            <AlertDialogDescription>
              {deleting && (
                <>
                  确定删除分组 <span className="font-semibold">{deleting.name}</span>？删除后用户侧将不再展示该组数据。
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteError && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-destructive">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{deleteError}</span>
            </div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault(); // 不让 Radix 自动关闭，由 handleConfirmDelete 控制关闭时机
                handleConfirmDelete();
              }}
              className="bg-red-500 hover:bg-red-600"
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
