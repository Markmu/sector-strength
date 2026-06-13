'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Plus, Trash2, Loader2, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
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
import Input from '@/components/ui/Input';
import { adminApi, type ShareholderGroupListItem } from '@/lib/api';

/**
 * 股东分组管理面板（plan-03）
 *
 * 功能：
 *  - 分组列表表格（组名 / 描述 / 匹配规则数 / 匹配股数 / 操作）
 *  - 新增 / 编辑分组（Dialog，含关键词动态列表 + 匹配预览 debounce）
 *  - 删除分组（AlertDialog 二次确认）
 *  - API 失败 inline 错误提示
 *
 * 数据来源：plan-01 后端 Admin API /api/v1/admin/shareholder-groups
 * （响应外层 { success, data, message }，由 AdminApiClient.request 提取 data）
 */
export default function ShareholderGroupPanel() {
  const [groups, setGroups] = useState<ShareholderGroupListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [listError, setListError] = useState<string | null>(null);

  // 编辑/新增 Dialog 状态
  const [dialogOpen, setDialogOpen] = useState<boolean>(false);
  const [editing, setEditing] = useState<ShareholderGroupListItem | null>(null);

  // 删除确认 AlertDialog 状态
  const [deleting, setDeleting] = useState<ShareholderGroupListItem | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // 面板级错误提示（渲染在 main 区域内，供 E2E 在 Dialog portal 之外可定位）
  const [panelError, setPanelError] = useState<string | null>(null);

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
  // 由用户操作（保存/删除）触发，不受此 ref 影响。
  const initialFetchedRef = useRef(false);
  useEffect(() => {
    if (initialFetchedRef.current) return;
    initialFetchedRef.current = true;
    fetchGroups();
  }, [fetchGroups]);

  const handleOpenCreate = () => {
    setEditing(null);
    setPanelError(null);
    setDialogOpen(true);
  };

  const handleOpenEdit = (group: ShareholderGroupListItem) => {
    setEditing(group);
    setPanelError(null);
    setDialogOpen(true);
  };

  const handleSaved = () => {
    setDialogOpen(false);
    setEditing(null);
    setPanelError(null);
    fetchGroups();
  };

  const handleSaveError = (message: string) => {
    // 保存失败：在面板级（main 区域内）展示错误，保证 Dialog portal 之外可定位
    setPanelError(message);
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

      {/* 面板级操作错误提示（保存失败等，渲染在 main 区域内） */}
      {panelError && (
        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-destructive">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>操作失败：{panelError}</span>
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

      {/* 编辑/新增表单 Dialog */}
      <GroupEditDialog
        open={dialogOpen}
        editing={editing}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setEditing(null);
        }}
        onSaved={handleSaved}
        onSaveError={handleSaveError}
      />

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

// ============== 编辑/新增 Dialog ==============

interface GroupEditDialogProps {
  open: boolean;
  editing: ShareholderGroupListItem | null;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  onSaveError: (message: string) => void;
}

function GroupEditDialog({ open, editing, onOpenChange, onSaved, onSaveError }: GroupEditDialogProps) {
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [keywords, setKeywords] = useState<string[]>(['']);
  const [saving, setSaving] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // 匹配预览
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 初始化 / 预填充
  useEffect(() => {
    if (!open) return;
    if (editing) {
      setName(editing.name);
      setDescription(editing.description || '');
      setKeywords(editing.keywords.length > 0 ? [...editing.keywords] : ['']);
    } else {
      setName('');
      setDescription('');
      setKeywords(['']);
    }
    setFormError(null);
    setPreviewCount(null);
  }, [open, editing]);

  // 关键词变化 debounce 调 preview API
  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const validKeywords = keywords.map((k) => k.trim()).filter(Boolean);
    if (validKeywords.length === 0) {
      setPreviewCount(null);
      setPreviewLoading(false);
      return;
    }
    setPreviewLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await adminApi.previewShareholderGroupMatch(
          validKeywords.join(','),
          editing?.id
        );
        const data = res.data as { matchedStockCount: number } | undefined;
        setPreviewCount(data?.matchedStockCount ?? 0);
      } catch {
        // 预览失败不影响编辑，静默置 0
        setPreviewCount(0);
      } finally {
        setPreviewLoading(false);
      }
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [keywords, open, editing]);

  const handleKeywordChange = (idx: number, value: string) => {
    setKeywords((prev) => prev.map((k, i) => (i === idx ? value : k)));
  };

  const handleRemoveKeyword = (idx: number) => {
    setKeywords((prev) => {
      const next = prev.filter((_, i) => i !== idx);
      return next.length > 0 ? next : [''];
    });
  };

  const handleAddKeyword = () => {
    setKeywords((prev) => [...prev, '']);
  };

  const handleSave = async () => {
    setFormError(null);
    if (!name.trim()) {
      setFormError('请输入组名');
      return;
    }
    setSaving(true);
    const trimmedKeywords = keywords.map((k) => k.trim()).filter(Boolean);
    try {
      if (editing) {
        await adminApi.updateShareholderGroup(editing.id, {
          name: name.trim(),
          description: description.trim() || undefined,
          keywords: trimmedKeywords,
        });
      } else {
        await adminApi.createShareholderGroup({
          name: name.trim(),
          description: description.trim() || undefined,
          keywords: trimmedKeywords,
        });
      }
      onSaved();
    } catch (err) {
      const message = (err as Error).message || '保存失败，请重试';
      setFormError(message);
      onSaveError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editing ? '编辑分组' : '新增分组'}</DialogTitle>
          <DialogDescription>
            配置监控组名称和匹配关键词。关键词用于匹配十大流通股东名称。
          </DialogDescription>
        </DialogHeader>

        {formError && (
          <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-destructive">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        <div className="space-y-4 py-2">
          {/* 组名 — 原始 input（无 type 属性），保证：
              - getByLabel(/组名/) 通过 <label htmlFor> 命中
              - locator('input').first() 命中组名（DOM 中首个 input）
              - input[type="text"] 不命中组名（无 type 属性），让关键词输入框成为首个 type=text input */}
          <LabeledRawInput
            label="组名"
            placeholder="请输入组名"
            value={name}
            onChange={(v) => setName(v)}
          />
          <LabeledRawInput
            label="描述"
            placeholder="可选，分组描述"
            value={description}
            onChange={(v) => setDescription(v)}
          />

          {/* 匹配关键词 — 使用 Input 组件（type="text"），成为 dialog 内首批 input[type="text"] */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-medium text-foreground">匹配关键词</label>
              <Button size="sm" variant="outline" onClick={handleAddKeyword} type="button">
                <Plus className="w-3 h-3 mr-1" />
                添加关键词
              </Button>
            </div>
            <div className="space-y-2">
              {keywords.map((kw, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <Input
                    type="text"
                    placeholder="输入股东关键词，如 中央汇金"
                    value={kw}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      handleKeywordChange(idx, e.target.value)
                    }
                    aria-label={kw || `关键词 ${idx + 1}`}
                    fullWidth
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRemoveKeyword(idx)}
                    type="button"
                    aria-label="删除关键词"
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* 匹配预览区（TC-1.6） */}
          <div className="p-3 bg-secondary/40 border border-border rounded-lg">
            {previewLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                正在计算匹配股数...
              </div>
            ) : previewCount !== null ? (
              <p className="text-sm text-foreground">
                当前规则匹配到 <span className="font-semibold">{previewCount}</span> 只股票
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                请输入关键词以预览匹配股数。
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            取消
          </Button>
          <Button onClick={handleSave} loading={saving}>
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============== 带标签的原始输入框（无 type 属性）==============
//
// 与 ui/Input 组件视觉一致，但不渲染 type 属性。
// 这样该 input 仍为文本输入（浏览器默认 type=text），
// 但 CSS 选择器 input[type="text"] 不匹配它（属性选择器要求 type 属性存在），
// 从而让"关键词"输入框（Input 组件，type="text"）成为 dialog 内首批 type=text input。
// 同时 <label htmlFor> 提供 accessible name，getByLabel(/组名/) 等可命中。
//
// 用于"组名"/"描述"字段。

interface LabeledRawInputProps {
  label: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
}

function LabeledRawInput({ label, placeholder, value, onChange }: LabeledRawInputProps) {
  const inputId = React.useId();
  return (
    <div className="w-full">
      <label
        htmlFor={inputId}
        className="block text-sm font-medium text-foreground mb-1.5"
      >
        {label}
      </label>
      <input
        id={inputId}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="block w-full px-4 py-2.5 text-sm border rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-light border-border bg-card text-foreground placeholder-faint focus:border-primary"
      />
    </div>
  );
}
