---
feat_id: "plan-02"
title: "前端编辑弹窗逐关键词股数与明细下钻"
dimension: frontend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02: 前端编辑弹窗逐关键词股数与明细下钻

## 1. 功能概要

- **目标**: 在 `GroupEditDialog` 编辑弹窗内逐关键词渲染「X 只」股数标签、「查看明细 ▾」按钮和明细展开区（三列表格 + 分页器 + 失败降级）；在 `adminApi` 对象内新增 2 个方法调用 plan-01 的 `/preview-breakdown` 和 `/keyword-matches` 端点；在 `helpers/mock-shareholder-api.ts` 内新增对应 mock，扩展 `shareholder-groups.spec.ts` 加入 5 个 Playwright 场景覆盖 AC-01~09。
- **完成后可观察结果**: 管理员打开「编辑分组」弹窗后，每个非空关键词行右侧立刻显示「X 只」标签（X 是该关键词单独匹配的去重股数）；底部仍展示「合并匹配 N 只股票」预览（与逐关键词股数并存）。点击某关键词的「查看明细」按钮，弹窗内就地展开三列表格（股票代码 + 股票名称 + 股东名称），按股票代码升序排列，同股票多股东分行展示；表格上方有分页器（默认每页 20 条）。修改关键词停顿后（500ms debounce），股数标签自动刷新；若明细已展开，明细内容同步刷新并重置到第 1 页。当后端 500 时，对应区域显示红色「加载失败 重试」按钮，但保存按钮始终可点击且能成功保存。空关键词行不显示「X 只」标签和「查看明细」按钮；0 匹配的关键词按钮置灰。
- **依赖**: plan-01（提供 `/preview-breakdown` 和 `/keyword-matches` 端点契约）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09]
- **涉及架构模块**: `adminApi`（新增 2 方法）、`GroupEditDialog`（state 扩展 + 渲染分支）、Playwright spec + mock helper
- **前置条件**:
  - plan-01 已完成（端点可调用，契约稳定）
  - `web/src/lib/api.ts` 的 `adminApi` 对象已存在（line 539-628）
  - `web/src/components/admin/ShareholderGroupPanel.tsx` 的 `GroupEditDialog` 已存在（line 291-535），含 500ms debounce 机制
  - `web/tests/e2e/shareholder-groups.spec.ts` 已存在（350 行）
  - `web/tests/e2e/helpers/mock-shareholder-api.ts` 已存在
  - Playwright 已安装（`cd web && npx playwright install`）
- **不在范围**:
  - 后端任何改动（plan-01 负责）
  - 分组列表表格行级「查看明细」入口（架构 §2.2 明确不做）
  - 关键词质量评分、误伤高亮（PRD §1.4 明确不做）
  - 明细数据导出（PRD §1.4 明确不做）
  - 用户侧 `/api/v1/shareholder-analysis/*` 改造
  - 持仓比例、持股数量等扩展列（明细仅三列）
  - 跨期变动方向（明细只看当前期）

## 2. 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/lib/api.ts` | 在 `adminApi` 对象内新增 `previewShareholderGroupMatchBreakdown` 和 `listShareholderGroupKeywordMatches` 两个方法（紧邻现有 `previewShareholderGroupMatch` line 618-627 之后） |
| modify | `web/src/components/admin/ShareholderGroupPanel.tsx` | 改造 `GroupEditDialog`：新增 3 个 state、改造现有 debounce useEffect、改造关键词行渲染、新增明细展开区 |
| modify | `web/tests/e2e/helpers/mock-shareholder-api.ts` | 新增 `createSocialGroup()` / `createSocialGroupWithEmptyAndZero()` 工厂 + `mockShareholderGroupPreviewBreakdown` / `mockShareholderGroupPreviewBreakdownError` / `mockShareholderGroupPreviewBreakdownSequence` / `mockShareholderGroupKeywordMatches` / `mockShareholderGroupKeywordMatchesError` helper（命名跟随现有 `mockShareholderGroup*` 系列，详见 §3 #8） |
| modify | `web/tests/e2e/shareholder-groups.spec.ts` | 追加 5 个 Playwright 场景覆盖 AC-01/02/03-05/06/07/08/09 |

## 3. 实现规格

### 前端部分

#### 1. `adminApi.previewShareholderGroupMatchBreakdown`

**位置**：`web/src/lib/api.ts` line 627（`previewShareholderGroupMatch` 的闭合 `}`）之后，line 628（`adminApi` 对象的闭合 `}`）之前。

**复用声明**：
- `adminApiClient`：`web/src/lib/api.ts:534` 导出，已实例化的 `AdminApiClient` 实例
- `adminApiClient.get<T>`：line 514-516，自动加 auth headers、提取 `response.data`、params 用 `url.searchParams`
- `URLSearchParams`：浏览器原生 API，与现有 `previewShareholderGroupMatch`（line 623）一致风格

**实现要点**：
```typescript
previewShareholderGroupMatchBreakdown: (
  keywords: string[],
  excludeGroupId?: number
) => {
  const params: Record<string, string> = {
    keywords: keywords.join(','),
  }
  if (excludeGroupId) params['exclude_group_id'] = String(excludeGroupId)
  // 与现有 previewShareholderGroupMatch 一致风格：手动 URLSearchParams 拼 endpoint，
  // 便于 E2E mock 用 pathname + search 精确匹配
  const search = new URLSearchParams(params).toString()
  return adminApiClient.get<{
    items: Array<{ keyword: string; matchedStockCount: number | null }>
  }>(`/admin/shareholder-groups/preview-breakdown?${search}`)
},
```

**前后端契约校验（四件套）**：
- 路径拼接：endpoint `/admin/shareholder-groups/preview-breakdown?keywords=...` × `adminApiClient.baseURL` `${API_BASE_URL}/api/v1`（line 8）= 实际请求 URL `${API_BASE_URL}/api/v1/admin/shareholder-groups/preview-breakdown?keywords=...`，与后端 `@router.get("/preview-breakdown")`（admin_router 在 `/v1/admin`、子 router 在 `/shareholder-groups`）拼出的 `/api/v1/admin/shareholder-groups/preview-breakdown` 完全一致，**无重复前缀**
- HTTP 方法：`adminApiClient.get` → GET；后端 `@router.get` → GET；一致
- query 参数命名：前端传 `keywords`（逗号分隔字符串）+ `exclude_group_id`（snake_case）；后端 `Query(keywords: str)` + `Query(exclude_group_id: Optional[int])`（snake_case）；**query 参数不经 Pydantic alias 转换**，命名必须 snake_case 完全一致
- 响应字段命名：后端响应 `data.items[].matchedStockCount`（camelCase，由 Pydantic `to_camel` 转换）；前端类型定义 `{ items: Array<{ keyword: string; matchedStockCount: number | null }> }`；一致

**响应解包层级**：`adminApiClient.get` 已自动提取 `response.data`（line 506），返回类型为 `ApiResponse<T>`，组件消费时 `res.data` 即 `T` 本身（即 `{ items: [...] }`）。

#### 2. `adminApi.listShareholderGroupKeywordMatches`

**位置**：紧邻 `previewShareholderGroupMatchBreakdown` 之后。

**实现要点**：
```typescript
listShareholderGroupKeywordMatches: (
  keyword: string,
  params: { page?: number; pageSize?: number; excludeGroupId?: number }
) => {
  const query: Record<string, string> = { keyword }
  // 注意：query 参数 snake_case（不经 alias 转换），用 page_size / exclude_group_id
  if (params.page) query['page'] = String(params.page)
  if (params.pageSize) query['page_size'] = String(params.pageSize)
  if (params.excludeGroupId) query['exclude_group_id'] = String(params.excludeGroupId)
  const search = new URLSearchParams(query).toString()
  return adminApiClient.get<{
    items: Array<{ symbol: string; stockName: string | null; holderName: string }>
    total: number
    page: number
    pageSize: number
  }>(`/admin/shareholder-groups/keyword-matches?${search}`)
},
```

**前后端契约校验（四件套）**：
- 路径拼接：endpoint `/admin/shareholder-groups/keyword-matches?keyword=...&page=...&page_size=...` × baseURL `/api/v1` = `/api/v1/admin/shareholder-groups/keyword-matches?...`，与后端路由拼出的实际路径一致，**无重复前缀**
- HTTP 方法：`adminApiClient.get` → GET；后端 `@router.get` → GET；一致
- query 参数命名：前端写 `keyword`、`page`、`page_size`（snake_case）、`exclude_group_id`（snake_case）；后端 `Query(keyword: str)` + `Query(page: int)` + `Query(page_size: int)` + `Query(exclude_group_id: Optional[int])`；**注意 `pageSize` 入参 → 写 query 时必须转 `page_size`**（这是常见的 query/response 风格陷阱）
- 响应字段命名：后端响应 `data.items[].symbol/stockName/holderName` + `data.total/page/pageSize`（camelCase）；前端类型定义用 `stockName` / `holderName` / `pageSize`；一致

#### 3. `GroupEditDialog` state 扩展

**位置**：`web/src/components/admin/ShareholderGroupPanel.tsx` line 301（`debounceRef` 声明）之后。

**新增 3 个 state**：
```tsx
// 逐关键词股数（按 keywords 数组索引映射）
const [perKeywordCounts, setPerKeywordCounts] = useState<
  Array<{ keyword: string; matchedStockCount: number | null; error?: boolean } | null
>(null);

// 当前展开明细的关键词索引（同时只能展开一个，ADR-4）
const [expandedKeywordIdx, setExpandedKeywordIdx] = useState<number | null>(null);

// 明细展开区的状态（loading / items / total / page / error）
const [detailState, setDetailState] = useState<{
  loading: boolean;
  items: Array<{ symbol: string; stockName: string | null; holderName: string }>;
  total: number;
  page: number;
  error: boolean;
} | null>(null);
```

**注意**：
- `perKeywordCounts` 用 `Array<...> | null` 表示未加载状态；空数组表示已加载但无关键词
- `expandedKeywordIdx` 用 `number | null` 表示当前展开的索引（按 `keywords` 数组的索引）；切换时自动收起前一个
- `detailState` 是单例（同时只对应 `expandedKeywordIdx` 指向的关键词）

**dialog 关闭时清理**：在现有 `useEffect(() => { if (!open) return; ... }, [open, editing])`（line 304-317）的 else 分支或额外 useEffect 内，添加 `setPerKeywordCounts(null); setExpandedKeywordIdx(null); setDetailState(null);`

#### 4. 改造现有 debounce useEffect（line 320-348）

**当前行为**（line 320-348）：
- 监听 `[keywords, open, editing]`
- 收集 `validKeywords = keywords.map(k => k.trim()).filter(Boolean)`
- 若为空 → `setPreviewCount(null)`；否则 500ms debounce 调 `previewShareholderGroupMatch`，catch 静默置 0

**改造后**（在现有 debounce setTimeout 回调内并行调用两个 API）：
```tsx
debounceRef.current = setTimeout(async () => {
  // 1. 合并预览（保留现有逻辑，AC-02）
  try {
    const res = await adminApi.previewShareholderGroupMatch(
      validKeywords.join(','),
      editing?.id
    );
    const data = res.data as { matchedStockCount: number } | undefined;
    setPreviewCount(data?.matchedStockCount ?? 0);
  } catch {
    setPreviewCount(0); // 现有 catch 行为不动
  }

  // 2. 逐关键词股数（新增，AC-01）
  try {
    const breakdownRes = await adminApi.previewShareholderGroupMatchBreakdown(
      validKeywords,
      editing?.id
    );
    const breakdown = breakdownRes.data as
      | { items: Array<{ keyword: string; matchedStockCount: number | null }> }
      | undefined;
    // 按 keywords 数组索引映射（不是按 keyword 字符串值，避免重复关键词混乱）
    const next: Array<{ keyword: string; matchedStockCount: number | null; error?: boolean }> = [];
    let itemIdx = 0;
    const items = breakdown?.items ?? [];
    keywords.forEach((kw) => {
      const trimmed = kw.trim();
      if (!trimmed) return; // 空关键词不填位（AC-08 前端过滤）
      const item = items[itemIdx++];
      next.push({
        keyword: kw,
        matchedStockCount: item?.matchedStockCount ?? null,
        error: item?.matchedStockCount === null,
      });
    });
    setPerKeywordCounts(next);
  } catch {
    // 整体请求失败 → 所有非空关键词置错误
    const next = keywords
      .filter((kw) => kw.trim())
      .map((kw) => ({ keyword: kw, matchedStockCount: null, error: true }));
    setPerKeywordCounts(next);
  } finally {
    setPreviewLoading(false);
  }
}, 500);
```

**关键规则**：
- 空 `validKeywords` 时除了清 `previewCount`，也要 `setPerKeywordCounts(null)`（AC-08）
- 后端按入参顺序返回相同 keyword 的多个 item，前端按索引映射（不是字符串匹配）
- 整体请求失败时所有关键词置 error 状态（前端 catch 兜底）

**已展开明细刷新（AC-06）**：在同一个 debounce 触发后，若 `expandedKeywordIdx !== null` 且对应关键词内容变化，重置 `detailState.page` 为 1 并重新加载明细。可在 debounce 回调末尾添加：
```tsx
if (expandedKeywordIdx !== null && detailState) {
  const currentKw = keywords[expandedKeywordIdx]?.trim();
  if (currentKw && currentKw !== detailState.lastKeyword) {
    reloadDetail(currentKw, 1); // 见 §3 #5
  }
}
```
（实现时需要给 `detailState` 加 `lastKeyword` 字段记录上次查询的关键词，或在 detail reload 函数里通过 closure 处理；具体由 implementer 决定，关键是触发 page=1 重新加载）

#### 5. 新增「查看明细」按钮 onClick 处理（`handleViewDetail`）

```tsx
const handleViewDetail = async (idx: number) => {
  const kw = keywords[idx]?.trim();
  if (!kw) return;
  // ADR-4：切换展开的关键词（自动收起前一个）
  if (expandedKeywordIdx === idx) {
    setExpandedKeywordIdx(null);
    setDetailState(null);
    return;
  }
  setExpandedKeywordIdx(idx);
  setDetailState({ loading: true, items: [], total: 0, page: 1, error: false });
  await reloadDetail(kw, 1);
};

const reloadDetail = async (keyword: string, page: number) => {
  setDetailState((prev) => prev ? { ...prev, loading: true, error: false } : prev);
  try {
    const res = await adminApi.listShareholderGroupKeywordMatches(keyword, {
      page,
      pageSize: 20,
      excludeGroupId: editing?.id,
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
    });
  } catch (err) {
    console.error('listShareholderGroupKeywordMatches failed', err);
    setDetailState({
      loading: false,
      items: [],
      total: 0,
      page,
      error: true, // AC-07：失败 → 显示重试按钮
    });
  }
};
```

#### 6. 关键词行渲染改造（line 442 区域）

**当前行为**：每行渲染关键词输入框 + 删除按钮。

**改造后**：每行追加「X 只」标签 + 「查看明细 ▾」按钮：
```tsx
{keywords.map((kw, idx) => {
  const trimmed = kw.trim();
  const countItem = perKeywordCounts?.find((_, i) => /* 按索引映射 */) ;
  // 简化：perKeywordCounts 与 keywords 同序构建，trimmed 非空的位置一一对应
  // 实现：构建一个 trimmedIndex → perKeywordCounts index 的映射

  return (
    <div key={idx} className="flex items-center gap-2">
      {/* 现有：关键词输入框 */}
      <input value={kw} onChange={(e) => handleKeywordChange(idx, e.target.value)} ... />
      {/* 现有：删除按钮 */}
      <button onClick={() => handleRemoveKeyword(idx)}>×</button>

      {/* 新增：仅当 trimmed 非空时显示股数标签 + 查看明细（AC-08） */}
      {trimmed && (
        <>
          {/* 股数标签 */}
          <span className="text-sm text-gray-500">
            {countItem?.error ? (
              <span className="text-destructive">
                加载失败 <button onClick={...}>重试</button>
              </span>
            ) : countItem?.matchedStockCount === 0 ? (
              '0 只'
            ) : countItem?.matchedStockCount != null ? (
              `${countItem.matchedStockCount} 只`
            ) : (
              '...' // loading
            )}
          </span>

          {/* 查看明细按钮（AC-09：count === 0 时 disabled） */}
          <button
            onClick={() => handleViewDetail(idx)}
            disabled={countItem?.matchedStockCount === 0 || countItem?.error}
            className="..."
          >
            查看明细 {expandedKeywordIdx === idx ? '▴' : '▾'}
          </button>
        </>
      )}
    </div>
  );
})}
```

**E2E 测试稳定选择器**（参照 .claude/rules/e2e-playwright-best-practices.md 规则 7）：
- 「X 只」标签：用 `data-testid="keyword-count-${idx}"` 或稳定的「N 只」+ `aria-label="关键词 ${keyword} 匹配股数"`
- 「查看明细」按钮：`data-testid="view-detail-${idx}"` 或 `getByRole('button', { name: /^查看明细/ })`
- 明细展开区：`data-testid="keyword-detail-panel"` 或 `getByRole('region', { name: '关键词明细' })`
- 避免依赖具体数字（X）做等待条件，依赖按钮可见性

**注意 .claude/rules/e2e-playwright-best-practices.md 规则 5（多元素匹配）**：
- 同页可能有多个「查看明细」按钮，必须用 `.filter({ hasText: ... })` 或 `data-testid` 缩小到具体行

#### 7. 明细展开区渲染（紧邻关键词行下方，仅当 `expandedKeywordIdx !== null` 时渲染）

```tsx
{expandedKeywordIdx !== null && detailState && (
  <div data-testid="keyword-detail-panel" className="border rounded p-3 mt-2 bg-gray-50">
    <div className="flex justify-between items-center mb-2">
      <span>
        关键词「{keywords[expandedKeywordIdx]?.trim()}」匹配明细 共 {detailState.total} 只
      </span>
      <button onClick={() => { setExpandedKeywordIdx(null); setDetailState(null); }}>
        收起
      </button>
    </div>

    {detailState.loading ? (
      <div>加载中...</div>
    ) : detailState.error ? (
      <div className="text-destructive">
        加载失败 <button onClick={() => reloadDetail(keywords[expandedKeywordIdx].trim(), detailState.page)}>重试</button>
      </div>
    ) : detailState.items.length === 0 ? (
      <div>暂无匹配数据</div>
    ) : (
      <>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th>股票代码</th>
              <th>股票名称</th>
              <th>股东名称</th>
            </tr>
          </thead>
          <tbody>
            {detailState.items.map((item, i) => (
              <tr key={`${item.symbol}-${item.holderName}-${i}`}>
                <td>{item.symbol}</td>
                <td>{item.stockName ?? '-' /* stocks 表缺失兜底 */}</td>
                <td>{item.holderName}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* 分页器 */}
        <div className="mt-2 flex justify-center gap-2 text-sm">
          <button
            disabled={detailState.page <= 1}
            onClick={() => reloadDetail(keywords[expandedKeywordIdx].trim(), detailState.page - 1)}
          >
            上一页
          </button>
          <span>
            {detailState.page} / {Math.max(1, Math.ceil(detailState.total / 20))}
          </span>
          <button
            disabled={detailState.page * 20 >= detailState.total}
            onClick={() => reloadDetail(keywords[expandedKeywordIdx].trim(), detailState.page + 1)}
          >
            下一页
          </button>
        </div>
      </>
    )}
  </div>
)}
```

**注意**：
- 同股票多股东天然相邻（后端 ORDER BY symbol ASC），前端不重排
- `stockName` 为 null 时显示「-」（架构 ADR-3）
- 翻页 onChange 重新调 `reloadDetail(kw, newPage)`，沿用 debounce 之外直接请求

#### 8. mock-shareholder-api.ts 扩展

**位置**：`web/tests/e2e/helpers/mock-shareholder-api.ts` 现有 helpers 之后。

**命名规则（重要）**：

新增 helper **必须跟随现有 `mockShareholderGroup*` 系列命名风格**（业务动词风格，不带 `Success` 后缀），与 `mockShareholderGroupsList` / `mockShareholderGroupPreview` / `mockShareholderGroupCreate` 保持一致。成功响应变体用「业务名词」（如 `mockShareholderGroupPreviewBreakdown`），错误响应变体追加 `Error` 后缀（参照现有 `mockShareholderGroupsListError` 风格）。**禁止使用 `mockXxxSuccess` / `mockXxxError` 风格**（与现有系列冲突，会让 implementer 困惑是否要重命名现有 helper）。

具体命名对照：

| 角色 | 命名（采用） | 禁用命名 |
| --- | --- | --- |
| preview-breakdown 成功 | `mockShareholderGroupPreviewBreakdown` | ~~`mockPreviewBreakdownSuccess`~~ |
| preview-breakdown 失败 | `mockShareholderGroupPreviewBreakdownError` | ~~`mockPreviewBreakdownError`~~ |
| keyword-matches 成功 | `mockShareholderGroupKeywordMatches` | ~~`mockKeywordMatchesSuccess`~~ |
| keyword-matches 失败 | `mockShareholderGroupKeywordMatchesError` | ~~`mockKeywordMatchesError`~~ |
| 测试数据工厂（社保组） | `createSocialGroup()` | ~~`createTestGroup(partial)`~~ |

**测试数据工厂**：跟随现有 `createQFiiGroup(): ShareholderGroupItem` 风格（无参 + 返回固定实例），新增 `createSocialGroup(): ShareholderGroupItem`。**不引入** `createTestGroup(partial)` 风格（与现有 `createQFiiGroup` / `createTestShareholderGroups` 不一致）。如需其他专用组（如多关键词组），按相同风格追加 `createXxxGroup()`。

**helper 函数签名清单**（implementer 必须按此签名实现）：

```typescript
// 工厂：返回单个"社保"测试组（与 createQFiiGroup 同风格，无参数）
export function createSocialGroup(): ShareholderGroupItem

// preview-breakdown 成功响应
export function mockShareholderGroupPreviewBreakdown(
  page: Page,
  items: Array<{ keyword: string; matchedStockCount: number | null }>
): Promise<void>

// preview-breakdown 失败响应（默认 500，参照 mockShareholderGroupsListError 风格）
export function mockShareholderGroupPreviewBreakdownError(
  page: Page,
  status: number = 500
): Promise<void>

// keyword-matches 成功响应
export function mockShareholderGroupKeywordMatches(
  page: Page,
  data: {
    items: Array<{ symbol: string; stockName: string | null; holderName: string }>
    total: number
    page: number
    pageSize: number
  }
): Promise<void>

// keyword-matches 失败响应（默认 500）
export function mockShareholderGroupKeywordMatchesError(
  page: Page,
  status: number = 500
): Promise<void>

// preview-breakdown 按调用次数返回不同结果（场景 3 实时刷新用，参照 mockShareholderGroupsList line 147-168 callIndex 模式）
export function mockShareholderGroupPreviewBreakdownSequence(
  page: Page,
  itemsList: Array<Array<{ keyword: string; matchedStockCount: number | null }>>
): Promise<void>

// 工厂：场景 5 用，含空关键词 + 0 匹配关键词
export function createSocialGroupWithEmptyAndZero(): ShareholderGroupItem
```

**实现要点**（参照现有 `mockShareholderGroupPreview` line 290-314 风格）：

```typescript
/**
 * 测试用"社保"分组（plan-02 场景 1~5 用，多关键词场景）
 */
export function createSocialGroup(): ShareholderGroupItem {
  return {
    id: 1,
    name: '社保',
    description: '全国社保基金测试组',
    isSystem: false,
    ruleCount: 2,
    matchedStockCount: 5,
    keywords: ['全国社保', '社保基金'],
  }
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/preview-breakdown — 逐关键词股数
 */
export async function mockShareholderGroupPreviewBreakdown(
  page: Page,
  items: Array<{ keyword: string; matchedStockCount: number | null }>
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/preview-breakdown'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { items } }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/preview-breakdown — 失败（默认 500）
 */
export async function mockShareholderGroupPreviewBreakdownError(
  page: Page,
  status: number = 500
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/preview-breakdown'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/keyword-matches — 关键词明细
 */
export async function mockShareholderGroupKeywordMatches(
  page: Page,
  data: {
    items: Array<{ symbol: string; stockName: string | null; holderName: string }>
    total: number
    page: number
    pageSize: number
  }
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/keyword-matches'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/keyword-matches — 失败（默认 500）
 */
export async function mockShareholderGroupKeywordMatchesError(
  page: Page,
  status: number = 500
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/keyword-matches'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}
```

**补充：场景 3 sequence 变体 + 场景 5 专用工厂**：

```typescript
/**
 * Mock GET /api/v1/admin/shareholder-groups/preview-breakdown — 按调用次数返回不同结果
 *
 * 场景 3（AC-06）实时刷新用，参照 mockShareholderGroupsList line 147-168 callIndex 模式
 */
export async function mockShareholderGroupPreviewBreakdownSequence(
  page: Page,
  itemsList: Array<Array<{ keyword: string; matchedStockCount: number | null }>>
): Promise<void> {
  let callIndex = 0
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/preview-breakdown'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const items = itemsList[Math.min(callIndex, itemsList.length - 1)] ?? []
      callIndex += 1
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { items } }),
      })
    }
  )
}

/**
 * 测试用"社保"分组变体（场景 5 用，含空关键词 + 0 匹配关键词）
 *
 * keywords: ['全国社保', '', '无匹配关键词']
 * 注意：空关键词位置（index 1）→ AC-08；0 匹配位置（index 2）→ AC-09
 */
export function createSocialGroupWithEmptyAndZero(): ShareholderGroupItem {
  return {
    id: 1,
    name: '社保',
    description: '场景 5 边界测试组',
    isSystem: false,
    ruleCount: 3,
    matchedStockCount: 2,
    keywords: ['全国社保', '', '无匹配关键词'],
  }
}
```

**注意**：
- 路径用 `matchApiPath(url, '/api/v1/admin/shareholder-groups/preview-breakdown')` 精确匹配 pathname（忽略 query）
- 沿用现有 `{ success: true, data: { items } }` 包裹结构；错误响应沿用 `{ detail: '...' }` 风格（与 `mockShareholderGroupsListError` line 173-188 一致）
- 所有 helper 必须 `async` + 显式 `route.fallback()` 非 GET 转交（参照 `mockShareholderGroupPreview` line 308-311）
- 多个 mock 在同 URL 注册时，遵循现有 helper 的 `route.fallback()` 转交规则（参照 line 22-39 注释）
- **注册顺序（重要）**：现有 `mockShareholderGroupPreview`（line 293-314）用 `matchApiPathPrefix` 前缀匹配 `/api/v1/admin/shareholder-groups/preview`，会同时捕获 `/preview-breakdown` 路径。Playwright route 是 LIFO（后注册的先执行），所以 spec 中必须**先**注册前缀匹配的 `mockShareholderGroupPreview`，**再**注册精确匹配的 `mockShareholderGroupPreviewBreakdown` —— 这样 LIFO 让精确匹配的 helper 优先命中 `/preview-breakdown` 请求，不命中时 fallback 给前缀匹配 helper；反之若顺序颠倒，前缀匹配会先捕获 `/preview-breakdown`，新 helper 永远不被调用，场景 1/2/3 会失败
- 场景 3 需要按调用次数返回不同数据时，参照 `mockShareholderGroupsList` line 147-168 的 `callIndex` 模式，**不要**用 `page.route('**/...')` 内联 mock（与 §3 #9 场景 3 风格统一要求一致）

#### 9. Playwright spec 扩展（追加 5 个场景到 `shareholder-groups.spec.ts`）

**位置**：`web/tests/e2e/shareholder-groups.spec.ts` 末尾追加，复用现有 `authedPage` fixture（line 22-53）与 `ADMIN_GROUPS_PAGE` 常量（line 14）。

**前置 import（追加到现有 import 列表 line 2-12）**：

```typescript
import {
  createTestShareholderGroups,
  createSocialGroup,                          // 新增（plan-02 §3 #8）
  createSocialGroupWithEmptyAndZero,          // 新增（plan-02 §3 #8）
  createQFiiGroup,
  mockShareholderGroupsList,
  mockShareholderGroupsListError,
  mockShareholderGroupCreate,
  mockShareholderGroupCreateConflict,
  mockShareholderGroupUpdate,
  mockShareholderGroupDelete,
  mockShareholderGroupPreview,
  mockShareholderGroupPreviewBreakdown,       // 新增（plan-02 §3 #8）
  mockShareholderGroupPreviewBreakdownError,  // 新增（plan-02 §3 #8）
  mockShareholderGroupPreviewBreakdownSequence,// 新增（plan-02 §3 #8，场景 3 用）
  mockShareholderGroupKeywordMatches,         // 新增（plan-02 §3 #8）
  mockShareholderGroupKeywordMatchesError,    // 新增（plan-02 §3 #8）
} from './helpers/mock-shareholder-api'
```

**统一约定**：
- 所有场景统一用 `await page.goto(ADMIN_GROUPS_PAGE)`（已含 `/dashboard` 前缀，与现有 spec 一致）
- 列表 mock 统一用 `mockShareholderGroupsList(page, [groups])`（嵌套数组，与现有 spec line 61/83 等一致）
- preview-breakdown / keyword-matches 用 §3 #8 新增 helper（命名跟随 `mockShareholderGroup*` 系列）
- 测试数据用 `createSocialGroup()` 工厂（无参，与 `createQFiiGroup()` 同风格），不要使用不存在的 `createTestGroup(partial)`

**场景 1（AC-01/02 逐关键词股数 + 合并预览并存）**：

```typescript
test('编辑弹窗显示逐关键词股数 + 合并预览（AC-01, AC-02）', async ({ page }) => {
  // mock 列表 → 点击编辑 → mock preview + preview-breakdown
  // 注册顺序遵循 §3 #8 LIFO 规则：先 Preview（前缀匹配 /preview，会捕获 /preview-breakdown），
  // 再 PreviewBreakdown（精确匹配 /preview-breakdown）—— LIFO 让精确匹配在 /preview-breakdown 请求上优先命中
  const group = createSocialGroup()
  await mockShareholderGroupsList(page, [group])
  await mockShareholderGroupPreview(page, 3) // 合并去重
  await mockShareholderGroupPreviewBreakdown(page, [
    { keyword: '全国社保', matchedStockCount: 2 },
    { keyword: '社保基金', matchedStockCount: 3 },
  ])

  await page.goto(ADMIN_GROUPS_PAGE)
  await page.getByRole('button', { name: /^编辑$/ }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()

  // AC-01：每个关键词行有「X 只」标签
  await expect(page.locator('[data-testid="keyword-count-0"]')).toContainText('2 只')
  await expect(page.locator('[data-testid="keyword-count-1"]')).toContainText('3 只')

  // AC-02：底部合并预览仍在
  await expect(page.getByText(/合并匹配\s*\d+\s*只/)).toBeVisible()
})
```

**场景 2（AC-03/04/05 查看明细 + 多股东分行 + 升序）**：

```typescript
test('点击查看明细展开三列表多股东分行按股票代码升序（AC-03, AC-04, AC-05）', async ({ page }) => {
  // mock 数据：600000 两个不同 holder + 600036 一个 holder
  const group = createSocialGroup()
  await mockShareholderGroupsList(page, [group])
  await mockShareholderGroupPreviewBreakdown(page, [
    { keyword: '全国社保', matchedStockCount: 3 },
  ])
  await mockShareholderGroupKeywordMatches(page, {
    items: [
      { symbol: '600000', stockName: '浦发银行', holderName: '全国社保基金一一六组合' },
      { symbol: '600000', stockName: '浦发银行', holderName: '全国社保基金一零四组合' },
      { symbol: '600036', stockName: '招商银行', holderName: '全国社保基金一零八组合' },
    ],
    total: 3,
    page: 1,
    pageSize: 20,
  })

  await page.goto(ADMIN_GROUPS_PAGE)
  await page.getByRole('button', { name: /^编辑$/ }).first().click()
  await page.getByRole('button', { name: /^查看明细/ }).first().click()

  // AC-03：三列表头
  await expect(page.getByRole('columnheader', { name: '股票代码' })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: '股票名称' })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: '股东名称' })).toBeVisible()

  // AC-04：600000 出现 2 行（不同 holderName）
  const rows = page.locator('[data-testid="keyword-detail-panel"] tbody tr')
  await expect(rows).toHaveCount(3)
  await expect(rows.nth(0).locator('td').nth(0)).toHaveText('600000')
  await expect(rows.nth(1).locator('td').nth(0)).toHaveText('600000')
  await expect(rows.nth(0).locator('td').nth(2)).not.toHaveText(
    await rows.nth(1).locator('td').nth(2).textContent()
  )

  // AC-05：升序
  const symbols = await rows.locator('td').nth(0).allTextContents()
  expect(symbols).toEqual([...symbols].sort())
})
```

**场景 3（AC-06 实时刷新）**：

> 说明：场景 3 需要按调用次数返回不同 preview-breakdown 数据。沿用现有 `mockShareholderGroupsList` 的 `callIndex` 模式（line 147-168），用 §3 #8 新增的 `mockShareholderGroupPreviewBreakdownSequence` helper，**不要**用 `page.route('**/...')` 内联 mock（与现有 spec 风格统一）。

```typescript
test('修改关键词后股数与已展开明细实时刷新（AC-06）', async ({ page }) => {
  const group = createSocialGroup()
  await mockShareholderGroupsList(page, [group])

  // preview-breakdown：第一次（初始加载）返回 2 只；第二次（修改后）返回 5 只
  await mockShareholderGroupPreviewBreakdownSequence(page, [
    [{ keyword: '全国社保', matchedStockCount: 2 }],
    [{ keyword: '全国社保基金', matchedStockCount: 5 }],
  ])
  // keyword-matches：固定返回 1 条
  await mockShareholderGroupKeywordMatches(page, {
    items: [
      { symbol: '600036', stockName: '招商银行', holderName: '全国社保基金一零八组合' },
    ],
    total: 1,
    page: 1,
    pageSize: 20,
  })

  await page.goto(ADMIN_GROUPS_PAGE)
  await page.getByRole('button', { name: /^编辑$/ }).first().click()
  await expect(page.locator('[data-testid="keyword-count-0"]')).toContainText('2 只')

  // 展开明细
  await page.getByRole('button', { name: /^查看明细/ }).first().click()

  // 修改关键词
  await page.locator('input[type="text"]').first().fill('全国社保基金')
  // 等 debounce 500ms + 重新加载
  await expect(page.locator('[data-testid="keyword-count-0"]')).toContainText('5 只')
  // 明细重置到第 1 页并重新加载
  await page.waitForTimeout(600)
})
```

**场景 4（AC-07 失败降级 + 保存可用）**：

```typescript
test('后端 500 时股数和明细显示重试按钮且保存可用（AC-07）', async ({ page }) => {
  const group = createSocialGroup()
  await mockShareholderGroupsList(page, [group])
  await mockShareholderGroupPreviewBreakdownError(page, 500)
  await mockShareholderGroupKeywordMatchesError(page, 500)
  await mockShareholderGroupsListError(page) // 合并预览也失败
  // 编辑保存 mock（沿用现有 mockShareholderGroupUpdate）
  await mockShareholderGroupUpdate(page, group)

  await page.goto(ADMIN_GROUPS_PAGE)
  await page.getByRole('button', { name: /^编辑$/ }).first().click()

  // AC-07：股数区显示重试（dialog 内）
  await expect(page.getByRole('dialog').getByText('加载失败').first()).toBeVisible()

  // 点击查看明细 → 明细区显示重试
  await page.getByRole('button', { name: /^查看明细/ }).first().click()
  await expect(
    page.locator('[data-testid="keyword-detail-panel"]').getByText('加载失败')
  ).toBeVisible()

  // 保存按钮可点击且成功
  const saveButton = page.getByRole('dialog').getByRole('button', { name: /^保存$/ })
  await expect(saveButton).toBeEnabled()
  await saveButton.click()
  // 弹窗关闭表示保存成功
  await expect(page.getByRole('dialog')).toBeHidden()
})
```

**场景 5（AC-08/AC-09 空关键词 + 0 匹配置灰）**：

> 说明：场景 5 的测试组需要在 `createSocialGroup()` 基础上改 keywords（加入空关键词与 0 匹配关键词）。沿用现有 `createQFiiGroup()` 的"返回固定实例"风格，不允许 `createTestGroup(partial)`。implementer 应在 §3 #8 增加专用工厂 `createSocialGroupWithEmptyAndZero()`（或类似命名，跟随 `createXxxGroup()` 系列），返回 `keywords: ['全国社保', '', '无匹配关键词']` 的测试组。

```typescript
test('空关键词不显示股数和按钮，0匹配按钮置灰（AC-08, AC-09）', async ({ page }) => {
  // 用专用工厂：含空关键词 + 0 匹配关键词
  // implementer 按 §3 #8 风格补 createSocialGroupWithEmptyAndZero()（无参，返回固定实例）
  const group = createSocialGroupWithEmptyAndZero()
  await mockShareholderGroupsList(page, [group])
  await mockShareholderGroupPreviewBreakdown(page, [
    { keyword: '全国社保', matchedStockCount: 2 },
    { keyword: '无匹配关键词', matchedStockCount: 0 },
  ])

  await page.goto(ADMIN_GROUPS_PAGE)
  await page.getByRole('button', { name: /^编辑$/ }).first().click()

  // AC-08：空关键词行（index 1）无 count 标签 + 无查看明细按钮
  await expect(page.locator('[data-testid="keyword-count-1"]')).toHaveCount(0)
  await expect(page.locator('[data-testid="view-detail-1"]')).toHaveCount(0)

  // AC-09：0 匹配关键词（index 2）的按钮 disabled
  await expect(page.locator('[data-testid="view-detail-2"]')).toBeDisabled()
  // 非 0 关键词（index 0）按钮 enabled
  await expect(page.locator('[data-testid="view-detail-0"]')).toBeEnabled()
})
```

**E2E 编写规则（参照 .claude/rules/e2e-playwright-best-practices.md）**：
- 规则 6：workers 已配置为 1（playwright.config.ts line 8），无需调整
- 规则 7：等待条件优先用按钮/role 而非具体文案；数字断言用 `toContainText` 而非 `toHaveText`
- 规则 5：多元素场景用 `data-testid` 索引或 `.filter({ hasText: ... })`
- mock URL：用 `matchApiPath(url, pathname)` 精确匹配，避免 glob 歧义
- 等待 debounce：用 `waitForResponse` 或 `waitForTimeout(600)`（500ms debounce + buffer）

**E2E 用例文档**：在 `docs/e2e/` 编写 `07-e2e-用例-股东分组匹配明细.md`（参照 06 风格），列出 5 个场景的步骤、断言、red/green 证据路径。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | red：在 `docs/e2e/07-e2e-用例-股东分组匹配明细.md` 编写 5 个场景的 Playwright 用例文档 | frontend | done | 含步骤、断言、red/green 证据路径 |
| 2 | red：扩展 `helpers/mock-shareholder-api.ts` 加入 5 个 mock helper + 2 个测试工厂 | frontend | done | `mockShareholderGroupPreviewBreakdown` / `mockShareholderGroupPreviewBreakdownError` / `mockShareholderGroupPreviewBreakdownSequence` + `mockShareholderGroupKeywordMatches` / `mockShareholderGroupKeywordMatchesError`（命名跟随现有 `mockShareholderGroup*` 系列）；`createSocialGroup()` + `createSocialGroupWithEmptyAndZero()` 工厂（无参，与 `createQFiiGroup()` 同风格）。详见 §3 #8 |
| 3 | red：追加 5 个场景到 `shareholder-groups.spec.ts` | frontend | done | 运行预期失败（组件未实现），证据见 `docs/e2e/evidence/plan-02-07-e2e-red-20260614.md` |
| 4 | 实现 `adminApi.previewShareholderGroupMatchBreakdown` | frontend | done | 紧邻现有 `previewShareholderGroupMatch` 之后 |
| 5 | 实现 `adminApi.listShareholderGroupKeywordMatches` | frontend | done | 紧邻 #4 之后；注意 query 用 snake_case `page_size` |
| 6 | 扩展 `GroupEditDialog` state（3 个）+ dialog 关闭清理 | frontend | done | `perKeywordCounts` / `expandedKeywordIdx` / `detailState` |
| 7 | 改造现有 debounce useEffect 同步调 breakdown API + 关键词索引映射 | frontend | done | 注意按 keywords 数组索引而非字符串值映射 |
| 8 | 改造关键词行渲染：追加「X 只」标签 + 「查看明细」按钮 + 稳定 data-testid | frontend | done | AC-08 空关键词过滤、AC-09 0 匹配 disabled |
| 9 | 新增明细展开区（三列表格 + 分页器 + 失败重试） | frontend | done | `stockName` 为 null 时显示「-」 |
| 10 | 实现 `handleViewDetail` + `reloadDetail` | frontend | done | ADR-4：切换关键词自动收起前一个 |
| 11 | green：运行 Playwright 5 个场景全部通过 | frontend | done | implementer 阶段已预验证 5 个场景全部通过；正式 green 证据由 test-e2e 阶段写入 `docs/e2e/evidence/plan-02-e2e-green-{date}.md` |

## 5. 验收标准

### 前端核心功能验收

- [ ] AC-01 每个非空关键词行右侧显示「X 只」标签（X = 该关键词单独匹配的去重股数）
- [ ] AC-02 底部「合并匹配 N 只股票」预览仍正常显示，与逐关键词股数并存
- [ ] AC-03 点击「查看明细」就地展开三列表格（股票代码 + 股票名称 + 股东名称）
- [ ] AC-04 同股票多股东 → 多行（symbol 相同、holderName 不同）
- [ ] AC-05 表格按 symbol 升序，同股票多行相邻（前端不重排，信任后端排序）
- [ ] AC-06 修改关键词停顿 500ms 后，股数标签自动刷新；若明细已展开，明细内容同步刷新并重置到第 1 页
- [ ] AC-07 后端 500 时，股数区/明细区显示红色「加载失败 重试」按钮；保存按钮始终 enabled 且能成功保存
- [ ] AC-08 空关键词行（`kw.trim() === ''`）不显示「X 只」标签和「查看明细」按钮
- [ ] AC-09 0 匹配关键词的「查看明细」按钮 `disabled`

### 类型与构建验收

- [ ] `cd web && npm run build` 通过，无 TypeScript 错误
- [ ] `cd web && npm run lint` 通过

### 前后端契约验收（对接 plan-01）

- [ ] `adminApi.previewShareholderGroupMatchBreakdown` 调用 `/api/v1/admin/shareholder-groups/preview-breakdown`，无重复前缀
- [ ] `adminApi.listShareholderGroupKeywordMatches` query 参数 `page_size`（snake_case，非 `pageSize`）
- [ ] 响应字段消费 `matchedStockCount` / `stockName` / `holderName` / `pageSize`（camelCase）
- [ ] `matchedStockCount === null` 时组件渲染错误状态（不与 0 混淆）

### 降级回归验收（架构 §8.2 + ADR-5）

- [ ] preview-breakdown 整体失败 → 所有非空关键词置 error（前端 catch 兜底）
- [ ] keyword-matches 失败 → 明细展开区显示错误 + 重试（不影响关键词行股数显示）
- [ ] preview（合并）失败 → 现有静默置 0 行为不变（与 06 一致）

### Playwright E2E 验收（E2E-TDD）

- [ ] **red 阶段**：在 `docs/e2e/07-e2e-用例-股东分组匹配明细.md` 编写 5 个场景的 Playwright 用例；在 `web/tests/e2e/shareholder-groups.spec.ts` 追加 5 个场景；在 `helpers/mock-shareholder-api.ts` 追加 4 个 mock helper。实现前运行 `npx playwright test tests/e2e/shareholder-groups.spec.ts` 预期失败，证据存 `docs/e2e/evidence/plan-02-e2e-red-{date}.md`
- [ ] **green 阶段**：实现完成后运行同一套 5 个场景全部通过（含既有 shareholder-groups 测试不破坏），证据存 `docs/e2e/evidence/plan-02-e2e-green-{date}.md`

### 全流程/集成验收（US 覆盖矩阵）

> 架构文档 §2.3 成功标准 + PRD §2.2 用户故事承接：US-01（逐关键词定位）/ US-02（保存前下钻）/ US-03（实时刷新）/ US-04（同股票多股东相邻）/ US-05（失败降级不阻塞）。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
| --- | --- | --- | --- |
| US-01 | 编辑时看到每个关键词分别匹配多少股 | plan-01, plan-02 | plan-02 §5 Playwright 场景 1 |
| US-02 | 保存前下钻查看具体匹配股票与股东 | plan-01, plan-02 | plan-02 §5 Playwright 场景 2 |
| US-03 | 修改关键词后股数与明细实时刷新 | plan-02 | plan-02 §5 Playwright 场景 3 |
| US-04 | 明细按股票代码升序，同股票多股东相邻 | plan-01, plan-02 | plan-02 §5 Playwright 场景 2 |
| US-05 | 明细加载失败不阻塞编辑和保存 | plan-01, plan-02 | plan-02 §5 Playwright 场景 4 |

- [ ] US-01 ~ US-05 全部可在编辑弹窗内走通（最终 Playwright 集成回归）
- [ ] 既有「新增/编辑/删除监控组」E2E 用例不受本期改动影响（green 阶段验证）

## 6. 验证命令

```bash
# 类型检查 + 构建
cd web && npm run build

# Lint
cd web && npm run lint

# red 阶段：预期失败（组件未实现 / mock 端点未实现）
cd web && npx playwright test tests/e2e/shareholder-groups.spec.ts -g "逐关键词股数|查看明细|修改关键词|失败降级|空关键词"

# green 阶段：全部通过
cd web && npx playwright test tests/e2e/shareholder-groups.spec.ts

# 仅跑本期新增场景（5 个）
cd web && npx playwright test tests/e2e/shareholder-groups.spec.ts --grep "AC-0[1-9]"

# 既有 shareholder-analysis 测试不应被破坏（本期未改动用户侧面板）
cd web && npx playwright test tests/e2e/shareholder-analysis.spec.ts

# 手动验证（启动 dev server + 后端）
cd web && npm run dev  # localhost:3100
# 浏览器：管理员登录 → 管理后台 → 股东分组管理 → 编辑 → 输入关键词 → 查看 X 只 + 点击查看明细
```

E2E（Playwright）是前端用户可观察功能的主质量门。开发必须先运行 red E2E 看到预期失败，再实现到 green 全部通过。

## 7. 交接上下文

- **架构章节**: §1 系统摘要、§3 用户流程与状态（含 §3.3 单关键词行状态机）、§4.2 模块职责（前端部分）、§5 ADR-4/5、§6.1~6.4 运行链路、§7.2 Schema（TS interface 视角）、§7.3 API 边界、§8.2 降级策略
- **相关代码**:
  - 现有 adminApi：`web/src/lib/api.ts:539-628`
  - 现有 GroupEditDialog：`web/src/components/admin/ShareholderGroupPanel.tsx:283-535`
    - debounce useEffect：line 320-348
    - 关键词行渲染：line 442
    - dialog 关闭 cleanup：line 304-317
  - 现有 Playwright spec：`web/tests/e2e/shareholder-groups.spec.ts`（350 行）
  - 现有 mock helper：`web/tests/e2e/helpers/mock-shareholder-api.ts`
  - 现有 mock 注释规范：mock-shareholder-api.ts line 22-39（URL pathname 匹配 + route.fallback 规则）
- **契约 / 数据对象**:
  - `KeywordCountItem` / `PreviewBreakdownData` / `KeywordMatchItem` / `KeywordMatchesData`（plan-01 §3 #5 定义）
  - 前端 TS interface：`{ items: Array<{ keyword: string; matchedStockCount: number | null }> }` 与 `{ items: Array<{ symbol: string; stockName: string | null; holderName: string }>; total: number; page: number; pageSize: number }`
  - `ApiResponse<T>` 外层包裹：`{ success, data, message }`；`AdminApiClient.request` 已自动提取 `data` 字段（`api.ts:506`）
- **下游消费方**: 无（plan-02 是最终用户可见功能；下游仅有 Playwright spec 作为质量门）
- **E2E 测试基础设施**:
  - Playwright config：`web/playwright.config.ts`（workers: 1, baseURL: localhost:3100, timeout: 30000, expect.timeout: 10000）
  - evidence 目录：`docs/e2e/evidence/`（red/green 证据）
  - 用例文档目录：`docs/e2e/`（参照 06 风格）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行。Task 1-3（red：用例文档 + mock + spec）必须先于 Task 4-10（实现）。Task 11（green）最后。
- **验证失败排查方向**:
  - red 阶段 E2E 报「元素未找到」→ 正常失败（组件未实现）
  - red 阶段 E2E 报「端点未匹配」→ 检查 mock helper URL 是否精确匹配 pathname
  - green 阶段某个场景一直 timeout → 检查 `data-testid` 是否正确加上、debounce 时间是否合理、selector 是否多元素匹配（规则 5）
  - 现有 shareholder-groups.spec.ts 既有场景失败 → 检查是否破坏了现有 props 接口或 debounce 行为
  - TypeScript 报类型错误 → 检查 `matchedStockCount: number | null` 的 null 处理是否完备
- **允许修改的额外文件**:
  - 如发现现有 mock helper 抽象不够复用，可在 `mock-shareholder-api.ts` 内新增辅助函数（不影响现有 helper）
  - 如发现 `GroupEditDialog` 组件需要拆子组件（明细展开区独立），可新建 `web/src/components/admin/KeywordDetailPanel.tsx`（保持父组件 props 不变）
- **暂停条件**:
  - E2E mock URL 匹配与现有 helper 模式冲突 → 暂停，参照 mock-shareholder-api.ts line 22-39 注释
  - 现有 `shareholder-groups.spec.ts` 既有场景因本期改动失败且无法快速修复 → 暂停，向用户确认是否调整既有测试
  - 某个 AC 在 Playwright 中难以稳定断言（如 debounce 时序）→ 暂停，与用户讨论是否改为单元测试或调整断言策略
- **E2E 不适用说明**: 不适用。本功能是用户可观察的前端能力，必须 Playwright E2E。
- **风险备注**:
  - **debounce 时序**：Playwright 等待 debounce 触发要预留 600ms+ buffer；场景 3 验证刷新时避免 race condition
  - **重复关键词索引映射**：草稿中允许重复关键词（如两个空行被填了相同内容），后端按入参顺序返回，前端必须按 `keywords` 数组索引（不是字符串值）映射，否则位置错乱
  - **`stockName` 为 null 的兜底**：渲染时显示「-」，避免 React 渲染 `null` 报错
  - **detail state 与 expandedKeywordIdx 同步**：切换关键词时务必先 reset `detailState` 再请求；关键词内容变化触发 debounce 时要重置 `detailState.page` 为 1（避免越界）
  - **同时只展开一个**：ADR-4 明确约束，避免多列表叠放 UX 复杂度

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 空关键词行（`kw.trim() === ''`） | 不渲染「X 只」标签和「查看明细」按钮（AC-08） | done |
| `matchedStockCount === null`（单关键词查询失败） | 显示「加载失败 重试」（AC-07） | done |
| `matchedStockCount === 0` | 显示「0 只」，按钮 disabled（AC-09） | done |
| `matchedStockCount` 加载中 | 显示「...」或骨架屏 | done |
| `stockName` 为 null | 显示「-」（stocks 表缺失兜底） | done |
| 明细 items 为空但 total > 0（翻页越界） | 翻页按钮 disabled；不会进入此状态（detail reload 总是从 page=1 重新加载） | done |
| 明细查询失败 | 明细区显示「加载失败 重试」按钮（AC-07） | done |
| 已展开明细的关键词被清空（`kw.trim() === ''`） | 自动收起明细：`setExpandedKeywordIdx(null); setDetailState(null)` | done |
| 翻页时关键词内容变化 | debounce 触发后重置 `detailState.page` 为 1 重新加载（避免页码越界） | done |
| dialog 关闭 | 清理 debounce timer + `perKeywordCounts` + `expandedKeywordIdx` + `detailState` | done |
| preview-breakdown 整体请求失败 | 所有非空关键词置 error（前端 catch 兜底） | done |
| 关键词数量很多（> 10） | 后端按关键词数 N 次单关键词查询；前端按索引映射渲染（不合并） | done |
| 草稿中重复关键词 | 后端按入参顺序返回，前端按 `keywords` 数组索引映射 | done |
| mock URL 多 helper 注册 | 用 `route.fallback()` 转交（参照现有 helper 注释） | done |
| Playwright strict mode violation（多元素匹配） | 用 `data-testid` + idx 或 `.filter({ hasText: ... })` 缩小（规则 5） | done |
| Playwright 等待 debounce 触发 | `waitForResponse` 或 `waitForTimeout(600)`（500ms debounce + buffer） | done |
