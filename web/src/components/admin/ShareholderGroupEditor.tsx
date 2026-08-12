'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Trash2, Loader2, AlertCircle, ArrowLeft } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { adminApi, type ShareholderGroupListItem } from '@/lib/api';

const LIST_PATH = '/dashboard/admin/shareholder-groups';

/**
 * 股东分组编辑器（整页表单，plan-03 重构）
 *
 * 由「弹窗 GroupEditDialog」迁移而来：新增 / 编辑共用同一表单，
 * 通过 mode 区分；编辑模式按 groupId 独立加载详情（URL 可刷新/可分享）。
 *
 * 功能（与原弹窗一致，仅外壳变化）：
 *  - 组名 / 描述 / 动态关键词列表
 *  - debounce 合并匹配预览
 *  - 逐关键词股数（plan-02 AC-01）
 *  - 查看明细展开 + 分页（plan-02 AC-03~AC-09）
 *  - 保存失败 inline 错误
 *
 * 所有 data-testid（keyword-count-N / view-detail-N / keyword-detail-panel）原样保留，
 * E2E 断言可直接复用。
 *
 * 数据来源：plan-01 后端 Admin API /api/v1/admin/shareholder-groups
 */
interface ShareholderGroupEditorProps {
  mode: 'create' | 'edit';
  groupId?: number;
}

export default function ShareholderGroupEditor({ mode, groupId }: ShareholderGroupEditorProps) {
  const router = useRouter();
  const isEdit = mode === 'edit';

  // edit 模式详情加载
  const [loading, setLoading] = useState<boolean>(isEdit);
  const [loadError, setLoadError] = useState<string | null>(null);

  // 表单状态
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [keywords, setKeywords] = useState<string[]>(['']);
  const [saving, setSaving] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // 匹配预览
  const [previewCount, setPreviewCount] = useState<number | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // plan-02：逐关键词股数（按 keywords 数组索引映射；后端按入参顺序返回）
  const [perKeywordCounts, setPerKeywordCounts] = useState<
    Array<{ keyword: string; matchedStockCount: number | null; error?: boolean }> | null
  >(null);

  // plan-02：当前展开明细的关键词索引（ADR-4：同时只能展开一个）
  const [expandedKeywordIdx, setExpandedKeywordIdx] = useState<number | null>(null);

  // plan-02：明细展开区状态（单例，对应 expandedKeywordIdx 指向的关键词）
  // lastKeyword 用于 debounce 触发后判断关键词内容是否变化，决定是否重置 page=1
  const [detailState, setDetailState] = useState<{
    loading: boolean;
    items: Array<{ symbol: string; stockName: string | null; holderName: string }>;
    total: number;
    page: number;
    error: boolean;
    lastKeyword?: string;
  } | null>(null);

  // edit 模式：按 groupId 加载详情预填充
  useEffect(() => {
    if (!isEdit || !groupId) return;
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    adminApi
      .getShareholderGroup(groupId)
      .then((res) => {
        if (cancelled) return;
        const g = res.data as ShareholderGroupListItem;
        setName(g.name);
        setDescription(g.description || '');
        setKeywords(g.keywords.length > 0 ? [...g.keywords] : ['']);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError((err as Error).message || '加载失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isEdit, groupId]);

  // 重新加载明细（独立 try/catch，AC-07 失败降级不抛错到顶层）
  const reloadDetail = useCallback(
    async (keyword: string, page: number) => {
      setDetailState((prev) => (prev ? { ...prev, loading: true, error: false } : prev));
      try {
        const res = await adminApi.listShareholderGroupKeywordMatches(keyword, {
          page,
          pageSize: 20,
          excludeGroupId: isEdit ? groupId : undefined,
        });
        const data = res.data as
          | {
              items: Array<{ symbol: string; stockName: string | null; holderName: string }>;
              total: number;
              page: number;
              pageSize: number;
            }
          | undefined;
        setDetailState({
          loading: false,
          items: data?.items ?? [],
          total: data?.total ?? 0,
          page: data?.page ?? page,
          error: false,
          lastKeyword: keyword,
        });
      } catch (err) {
        console.error('listShareholderGroupKeywordMatches failed', err);
        setDetailState({
          loading: false,
          items: [],
          total: 0,
          page,
          error: true,
          lastKeyword: keyword,
        });
      }
    },
    [isEdit, groupId]
  );

  // 关键词变化 debounce 调 preview + preview-breakdown
  useEffect(() => {
    // edit 模式详情未加载完不触发预览（表单还是空的）
    if (isEdit && loading) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const validKeywords = keywords.map((k) => k.trim()).filter(Boolean);
    if (validKeywords.length === 0) {
      setPreviewCount(null);
      setPreviewLoading(false);
      setPerKeywordCounts(null); // AC-08：无关键词时清空股数
      return;
    }
    setPreviewLoading(true);
    // 用 ref 暂存当前 detailState/expandedKeywordIdx，避免把它们放入依赖导致每次 setState
    // 后 debounce timer 都被重置（陷入死循环）
    const currentDetailState = detailState;
    const currentExpandedIdx = expandedKeywordIdx;
    const excludeGroupId = isEdit ? groupId : undefined;
    debounceRef.current = setTimeout(async () => {
      // 1. 合并预览（保留现有逻辑，AC-02）
      try {
        const res = await adminApi.previewShareholderGroupMatch(
          validKeywords.join(','),
          excludeGroupId
        );
        const data = res.data as { matchedStockCount: number } | undefined;
        setPreviewCount(data?.matchedStockCount ?? 0);
      } catch {
        // 预览失败不影响编辑，静默置 0（与 06 一致）
        setPreviewCount(0);
      }

      // 2. 逐关键词股数（AC-01）
      try {
        const breakdownRes = await adminApi.previewShareholderGroupMatchBreakdown(
          validKeywords,
          excludeGroupId
        );
        const breakdown = breakdownRes.data as
          | { items: Array<{ keyword: string; matchedStockCount: number | null }> }
          | undefined;
        // 按 keywords 数组索引映射（不是按 keyword 字符串值，避免重复关键词错位）
        const next: Array<{
          keyword: string;
          matchedStockCount: number | null;
          error?: boolean;
        }> = [];
        let itemIdx = 0;
        const items = breakdown?.items ?? [];
        keywords.forEach((kw) => {
          const trimmed = kw.trim();
          if (!trimmed) return; // AC-08 前端过滤空关键词
          const item = items[itemIdx++];
          next.push({
            keyword: kw,
            matchedStockCount: item?.matchedStockCount ?? null,
            error: item?.matchedStockCount === null || item === undefined,
          });
        });
        setPerKeywordCounts(next);
      } catch {
        // 整体请求失败 → 所有非空关键词置 error 状态（AC-07 前端兜底）
        const next = keywords
          .filter((kw) => kw.trim())
          .map((kw) => ({ keyword: kw, matchedStockCount: null, error: true }));
        setPerKeywordCounts(next);
      } finally {
        setPreviewLoading(false);
      }

      // 3. AC-06：已展开明细的关键词内容变化 → 重置 page=1 重新加载
      if (currentExpandedIdx !== null && currentDetailState) {
        const currentKw = keywords[currentExpandedIdx]?.trim();
        if (currentKw && currentKw !== currentDetailState.lastKeyword) {
          await reloadDetail(currentKw, 1);
        } else if (!currentKw) {
          // 已展开明细的关键词被清空 → 自动收起（边界场景）
          setExpandedKeywordIdx(null);
          setDetailState(null);
        }
      }
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // 故意不把 detailState / expandedKeywordIdx 放入依赖：每次它们变化会重置 debounce
    // timer 导致循环；改为读取 effect 触发瞬间的快照值
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keywords, isEdit, groupId, loading, reloadDetail]);

  // 切换明细展开（ADR-4：切换关键词自动收起前一个）
  const handleViewDetail = async (idx: number) => {
    const kw = keywords[idx]?.trim();
    if (!kw) return;
    if (expandedKeywordIdx === idx) {
      // 再次点击同一个 → 收起
      setExpandedKeywordIdx(null);
      setDetailState(null);
      return;
    }
    setExpandedKeywordIdx(idx);
    setDetailState({
      loading: true,
      items: [],
      total: 0,
      page: 1,
      error: false,
      lastKeyword: kw,
    });
    await reloadDetail(kw, 1);
  };

  // 重试单关键词股数（AC-07）
  const handleRetryBreakdown = async () => {
    const validKeywords = keywords.map((k) => k.trim()).filter(Boolean);
    if (validKeywords.length === 0) return;
    const excludeGroupId = isEdit ? groupId : undefined;
    try {
      const breakdownRes = await adminApi.previewShareholderGroupMatchBreakdown(
        validKeywords,
        excludeGroupId
      );
      const breakdown = breakdownRes.data as
        | { items: Array<{ keyword: string; matchedStockCount: number | null }> }
        | undefined;
      const next: Array<{
        keyword: string;
        matchedStockCount: number | null;
        error?: boolean;
      }> = [];
      let itemIdx = 0;
      const items = breakdown?.items ?? [];
      keywords.forEach((kw) => {
        const trimmed = kw.trim();
        if (!trimmed) return;
        const item = items[itemIdx++];
        next.push({
          keyword: kw,
          matchedStockCount: item?.matchedStockCount ?? null,
          error: item?.matchedStockCount === null || item === undefined,
        });
      });
      setPerKeywordCounts(next);
    } catch {
      const next = keywords
        .filter((kw) => kw.trim())
        .map((kw) => ({ keyword: kw, matchedStockCount: null, error: true }));
      setPerKeywordCounts(next);
    }
  };

  const handleKeywordChange = (idx: number, value: string) => {
    setKeywords((prev) => prev.map((k, i) => (i === idx ? value : k)));
  };

  const handleRemoveKeyword = (idx: number) => {
    setKeywords((prev) => {
      const next = prev.filter((_, i) => i !== idx);
      return next.length > 0 ? next : [''];
    });
    // 移除关键词后若展开的就是被移除行，自动收起
    if (expandedKeywordIdx === idx) {
      setExpandedKeywordIdx(null);
      setDetailState(null);
    } else if (expandedKeywordIdx !== null && expandedKeywordIdx > idx) {
      // 被移除行在前 → 索引前移
      setExpandedKeywordIdx(expandedKeywordIdx - 1);
    }
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
      if (isEdit && groupId) {
        await adminApi.updateShareholderGroup(groupId, {
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
      // 保存成功 → 回列表（列表刷新展示最新结果）
      router.push(LIST_PATH);
    } catch (err) {
      setFormError((err as Error).message || '保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // 构建 keywords 数组索引 → perKeywordCounts 索引的映射
  // （perKeywordCounts 跳过空关键词，与 keywords trimmed 非空行一一对应）
  const getCountItemForIdx = (idx: number) => {
    if (!perKeywordCounts) return undefined;
    let nonEmptySeen = -1;
    for (let i = 0; i <= idx; i++) {
      if (keywords[i]?.trim()) nonEmptySeen += 1;
    }
    return nonEmptySeen >= 0 ? perKeywordCounts[nonEmptySeen] : undefined;
  };

  // edit 模式详情加载中
  if (isEdit && loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin" />
        加载中...
      </div>
    );
  }

  // edit 模式详情加载失败
  if (isEdit && loadError) {
    return (
      <div className="space-y-4">
        <div className="flex items-start gap-2 p-3 bg-rise/10 border border-rise/30 rounded-lg text-sm text-destructive">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>加载失败：{loadError}</span>
        </div>
        <button
          onClick={() => router.push(LIST_PATH)}
          className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回列表
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 返回列表链接 */}
      <button
        onClick={() => router.push(LIST_PATH)}
        className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        返回列表
      </button>

      {formError && (
        <div className="flex items-start gap-2 p-3 bg-rise/10 border border-rise/30 rounded-lg text-sm text-destructive">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      <div className="space-y-4">
        {/* 组名 - 原始 input（无 type 属性），保证：
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

        {/* 匹配关键词 - 使用 Input 组件（type="text"），成为页面内首批 input[type="text"] */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm font-medium text-foreground">匹配关键词</label>
            <Button size="sm" variant="outline" onClick={handleAddKeyword} type="button">
              <Plus className="w-3 h-3 mr-1" />
              添加关键词
            </Button>
          </div>
          <div className="space-y-2">
            {keywords.map((kw, idx) => {
              const trimmed = kw.trim();
              const countItem = getCountItemForIdx(idx);
              const isExpanded = expandedKeywordIdx === idx;
              return (
                <div key={idx}>
                  <div className="flex items-center gap-2">
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

                    {/* plan-02：仅当 trimmed 非空时显示股数标签 + 查看明细按钮（AC-08） */}
                    {trimmed && (
                      <>
                        {/* 股数标签 */}
                        <span
                          data-testid={`keyword-count-${idx}`}
                          className="text-sm text-muted-foreground whitespace-nowrap"
                        >
                          {countItem?.error ? (
                            <span className="text-destructive inline-flex items-center gap-1">
                              加载失败
                              <button
                                type="button"
                                onClick={handleRetryBreakdown}
                                className="text-primary underline"
                              >
                                重试
                              </button>
                            </span>
                          ) : countItem?.matchedStockCount === 0 ? (
                            '0 只'
                          ) : countItem?.matchedStockCount != null ? (
                            `${countItem.matchedStockCount} 只`
                          ) : (
                            '...'
                          )}
                        </span>

                        {/* 查看明细按钮（AC-09：count === 0 时 disabled；加载中 / error 时仍可点） */}
                        <Button
                          size="sm"
                          variant="outline"
                          type="button"
                          data-testid={`view-detail-${idx}`}
                          onClick={() => handleViewDetail(idx)}
                          disabled={countItem?.matchedStockCount === 0}
                        >
                          查看明细 {isExpanded ? '▴' : '▾'}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* plan-02：明细展开区（紧邻关键词行下方，仅当 expandedKeywordIdx !== null 时渲染） */}
        {expandedKeywordIdx !== null && detailState && (
          <div
            data-testid="keyword-detail-panel"
            className="border border-border rounded-lg p-3 mt-2 bg-secondary/30"
          >
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-foreground">
                关键词「{keywords[expandedKeywordIdx]?.trim()}」匹配明细 共{' '}
                {detailState.total} 只
              </span>
              <Button
                size="sm"
                variant="ghost"
                type="button"
                onClick={() => {
                  setExpandedKeywordIdx(null);
                  setDetailState(null);
                }}
              >
                收起
              </Button>
            </div>

            {detailState.loading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                加载中...
              </div>
            ) : detailState.error ? (
              <div className="text-destructive text-sm inline-flex items-center gap-1">
                加载失败
                <button
                  type="button"
                  onClick={() =>
                    reloadDetail(keywords[expandedKeywordIdx].trim(), detailState.page)
                  }
                  className="text-primary underline"
                >
                  重试
                </button>
              </div>
            ) : detailState.items.length === 0 ? (
              <div className="text-sm text-muted-foreground">暂无匹配数据</div>
            ) : (
              <>
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      <th className="text-left px-2 py-1.5 font-medium text-muted-foreground">
                        股票代码
                      </th>
                      <th className="text-left px-2 py-1.5 font-medium text-muted-foreground">
                        股票名称
                      </th>
                      <th className="text-left px-2 py-1.5 font-medium text-muted-foreground">
                        股东名称
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {detailState.items.map((item, i) => (
                      <tr key={`${item.symbol}-${item.holderName}-${i}`} className="border-t border-border">
                        <td className="px-2 py-1.5">{item.symbol}</td>
                        <td className="px-2 py-1.5">{item.stockName ?? '-'}</td>
                        <td className="px-2 py-1.5">{item.holderName}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* 分页器（默认每页 20 条） */}
                <div className="mt-2 flex justify-center items-center gap-2 text-sm">
                  <Button
                    size="sm"
                    variant="outline"
                    type="button"
                    disabled={detailState.page <= 1}
                    onClick={() =>
                      reloadDetail(keywords[expandedKeywordIdx].trim(), detailState.page - 1)
                    }
                  >
                    上一页
                  </Button>
                  <span>
                    {detailState.page} / {Math.max(1, Math.ceil(detailState.total / 20))}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    type="button"
                    disabled={detailState.page * 20 >= detailState.total}
                    onClick={() =>
                      reloadDetail(keywords[expandedKeywordIdx].trim(), detailState.page + 1)
                    }
                  >
                    下一页
                  </Button>
                </div>
              </>
            )}
          </div>
        )}

        {/* 匹配预览区（TC-1.6） */}
        <div className="p-3 bg-secondary/40 border border-border rounded-lg">
          {previewLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              正在计算匹配股数...
            </div>
          ) : previewCount !== null ? (
            <p className="text-sm text-foreground">
              合并匹配 <span className="font-semibold">{previewCount}</span> 只股票
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">请输入关键词以预览匹配股数。</p>
          )}
        </div>
      </div>

      {/* 底部操作按钮 */}
      <div className="flex items-center justify-end gap-2 pt-4 border-t border-border">
        <Button
          variant="outline"
          onClick={() => router.push(LIST_PATH)}
          disabled={saving}
        >
          取消
        </Button>
        <Button onClick={handleSave} loading={saving}>
          保存
        </Button>
      </div>
    </div>
  );
}

// ============== 带标签的原始输入框（无 type 属性）==============
//
// 与 ui/Input 组件视觉一致，但不渲染 type 属性。
// 这样该 input 仍为文本输入（浏览器默认 type=text），
// 但 CSS 选择器 input[type="text"] 不匹配它（属性选择器要求 type 属性存在），
// 从而让"关键词"输入框（Input 组件，type="text"）成为页面内首批 type=text input。
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
      <label htmlFor={inputId} className="block text-sm font-medium text-foreground mb-1.5">
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
