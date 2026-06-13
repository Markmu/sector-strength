# 开发计划复查报告

## 一、检查对象

- **架构文档**：`docs/06-股东分析面板/06-1-架构文档-股东分析面板.md`
- **实现计划**：`docs/06-股东分析面板/06-2-实现计划-股东分析面板/`
- **功能数**：4（plan-01 ~ plan-04）
- **前次检查**：`dev-plan-check-20260613.md`（8 项建议，标注已应用）

## 二、总评

- **结论**：通过（有 1 个新发现问题）
- **阻塞问题数**：0
- **建议项数**：1（新发现）+ 0（前次 8 项已验证应用）

前次检查的 8 项建议已全部正确应用到计划文件中。本次复查发现 1 个新问题（plan-03 AdminSidebar navItem 缺少必填 `icon` 字段），不影响架构继承完整性，但会导致前端 TypeScript 编译失败。

## 三、前次建议应用验证

| 建议项 | 验证结果 | 证据 |
| --- | --- | --- |
| S-01 E2E-TDD 验证项 | ✅ 已应用 | plan-04 §8 风险与边界已补充 Playwright E2E 计划，含 red/green TDD、docs/e2e/ 路径 |
| S-02 _get_report_periods 内部方法 | ✅ 已应用 | plan-02 §3 Task 1 已独立为 `_get_report_periods()` 内部方法，含完整参数和返回值说明 |
| S-03 SectorStock 显式 JOIN | ✅ 已应用 | plan-02 §3 `_get_industry_for_stocks` 已添加注意事项，明确 `sector_code`/`stock_code` 字符串关联、需显式 SQLAlchemy core join |
| S-04 avg_hold_float_ratio 聚合语义 | ✅ 已应用 | plan-02 §3.3 get_summary 已添加详细注释：先按股票 SUM，再对股票集合求 AVG |
| S-05 modify 文件定位策略 | ✅ 已应用 | plan-01 §2 文件清单 modify 行已补充"追加 import 语句和注册新 Model 到 __all__" |
| S-06 require_admin import 路径 | ✅ 已应用 | plan-01 §3.4 已补充 `from src.api.deps import require_admin` import 路径 |
| S-07 BaseRepository 方法覆盖说明 | ✅ 已应用 | plan-01 §3.2 已添加"BaseRepository 基本方法使用说明"段落，明确何时用基本方法、何时用自定义方法 |
| S-08 多组联合查询去重语义 | ✅ 已应用 | plan-02 §3 `_match_holdings` 已添加引用块详细说明多组关键词合并 + (symbol, holder_name) 去重语义 |

## 四、新发现问题

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| ⚠️ 建议 | plan-03 §3.4 更新 AdminSidebar | **AdminSidebar navItem 缺少必填 `icon` 字段**。实际代码中 `NavItem` 接口定义 `icon` 为必填字段（`icon: React.ComponentType<{ className?: string }>`，无 `?` 修饰符），但 plan-03 给出的新增项为 `{ id: 'shareholder-groups', label: '股东分组管理', href: '/dashboard/admin/shareholder-groups' }`，缺少 `icon` 属性，会导致 TypeScript 编译报错。AdminSidebar 已从 `lucide-react` 导入了 `Users` 图标，可直接复用 | 将 plan-03 §3.4 修改为：`{ id: 'shareholder-groups', label: '股东分组管理', icon: Users, href: '/dashboard/admin/shareholder-groups', description: '股东分组和匹配规则管理' }`。`Users` 图标已在现有 imports 中（与 DashboardLayout 使用同一图标名，语义一致） |

### 问题详细说明

**AdminSidebar.tsx 的 NavItem 接口**（必填 icon）：
```typescript
interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;  // 必填，无 ?
  href: string;
  description?: string;
}
```

**现有 navItems 示例**（均含 icon）：
```typescript
{ id: 'dashboard', label: '仪表板', icon: LayoutDashboard, href: '/dashboard/admin', description: '系统概览和统计' }
{ id: 'fund-init', label: '基金同步', icon: Landmark, href: '/dashboard/admin/fund-init', description: '基金数据采集和同步' }
```

**plan-03 当前写法**（缺少 icon）：
```typescript
{ id: 'shareholder-groups', label: '股东分组管理', href: '/dashboard/admin/shareholder-groups' }
```

**应修改为**：
```typescript
{ id: 'shareholder-groups', label: '股东分组管理', icon: Users, href: '/dashboard/admin/shareholder-groups', description: '股东分组和匹配规则管理' }
```

## 五、复查结论

- 架构文档 AC-01 ~ AC-11 全部正确映射到 README 和 FEAT
- 7 条 ADR 全部以"实施护栏"形式体现
- 数据契约、API 边界、运行链路、模块职责均完整继承
- 复用声明（top10_float_holders、sectors/sector_stocks、BaseRepository、require_admin、AdminApiClient）均已验证可行
- 前次 8 项建议全部正确应用到计划文件中
- **唯一新发现**：plan-03 §3.4 AdminSidebar navItem 缺少必填 `icon` 字段，建议补丁后即可执行
