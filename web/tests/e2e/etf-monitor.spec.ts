import { test as base, expect, type Page } from '@playwright/test'
import { installFullFundFlowMocks } from './helpers/mock-sector-fund-flow-api'
import {
  installEtfMonitorMocks,
  mockEtfIndexRankings,
  mockEtfIndexRankingsEmpty,
  mockEtfIndexRankingsError,
  mockEtfIndexDetail,
  mockEtfTrend,
  mockEtfLatestDate,
} from './helpers/mock-etf-monitor-api'

/**
 * ETF 监控页 E2E spec（14 期 plan-04 前端基础设施 / plan-05 监控页面）
 *
 * 本文件由 test-e2e skill 在 plan-04 red-e2e 阶段创建，覆盖 AC-01~AC-11/AC-13。
 *
 * 用例分层策略（与 plan-04/05 实现边界对齐）：
 * - **plan-04 范围（导航 + 路由壳）**：入口存在、点击跳转、页面空载渲染、
 *   降级回归（现有导航不受影响）。这些用例依赖 plan-04 的 DashboardLayout 导航项 +
 *   /dashboard/etf-monitor 路由壳，已随 plan-04 green 通过。
 * - **plan-05 范围（业务交互）**：排行表四态、维度/排序/分页切换、明细展开、趋势曲线、
 *   错误重试、排行→趋势跳转。这些用例依赖 plan-05 的 EtfMonitorPage 业务组件，由
 *   installEtfMonitorMocks（mock-etf-monitor-api.ts）mock etfMonitorApi 4 个端点。
 *   plan-05 red 阶段：业务组件未实现（page.tsx 仍是占位空壳），TC-5.1~5.12 因
 *   data-testid 不存在（排行表/趋势图未渲染）而预期失败。
 *
 * 认证：复用 fund-crowd-analysis.spec.ts / broker-recommend-analysis.spec.ts 范式——
 * 本项目自定义 JWT（token 存 localStorage + Cookie access_token），非 NextAuth。
 * /dashboard 无服务端路由守卫（无 middleware.ts），侧边栏在所有 dashboard 页渲染。
 */

const ETF_MONITOR_PAGE = '/dashboard/etf-monitor'
const SECTOR_FUND_FLOW_PAGE = '/dashboard/sector-fund-flow'

/**
 * 普通用户认证 fixture（复用 broker-recommend-analysis.spec.ts:27-53 范式）
 */
const test = base.extend<{ authedPage: void }>({
  authedPage: [
    async ({ page }, use) => {
      await page.context().addCookies([
        { name: 'access_token', value: 'test-mock-jwt-token', domain: 'localhost', path: '/' },
      ])
      await page.addInitScript(() => {
        localStorage.setItem('accessToken', 'test-mock-jwt-token')
        localStorage.setItem('refreshToken', 'test-mock-refresh-token')
        localStorage.setItem('tokenType', 'Bearer')
        localStorage.setItem('expiresIn', '3600')
        localStorage.setItem(
          'user',
          JSON.stringify({
            id: 'test-user-id',
            email: 'user@test.com',
            username: 'TestUser',
            is_active: true,
            role: 'user',
          })
        )
      })
      await use()
    },
    { auto: true },
  ],
})

// ============================================================================
// plan-04：导航入口与路由壳（TC-4.1~4.6 已随 plan-04 green 通过）
// ============================================================================

test.describe('plan-04：ETF 监控导航入口与路由壳', () => {
  test.describe('导航入口存在（plan-04 §5：侧边栏出现"ETF 监控"）', () => {
    test('TC-4.1 侧边栏存在"ETF 监控"导航项', async ({ page }) => {
      // 进入任一 dashboard 页（侧边栏在所有 dashboard 页渲染）
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 断言：侧边栏存在"ETF 监控"导航项（Sidebar 渲染 <Link>{title}</Link>）
      const menuLink = page.getByRole('link', { name: 'ETF 监控' })
      await expect(menuLink).toBeVisible()
      await expect(menuLink).toHaveAttribute('href', '/dashboard/etf-monitor')
    })

    test('TC-4.2 ETF 监控导航项位于"板块资金流"之后', async ({ page }) => {
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 导航项顺序：板块资金流 -> ETF 监控（plan-04 §3 #5）
      const navLinks = page
        .locator('nav a')
        .filter({ hasText: /板块资金流|ETF 监控/ })
      await expect(navLinks).toHaveCount(2)
      await expect(navLinks.first()).toContainText('板块资金流')
      await expect(navLinks.last()).toContainText('ETF 监控')
    })
  })

  test.describe('点击导航跳转（AC-01 入口路径，plan-04 §5 E2E）', () => {
    test('TC-4.3 点击"ETF 监控"导航跳转到 /dashboard/etf-monitor', async ({ page }) => {
      // sector-fund-flow 源页会向真实后端发起 SWR 请求；spec 用 mock token 会被后端
      // 401 拒绝，apiClient 的 401 分支会触发 handleUnauthorizedRedirect 跳转 /login，
      // 导致导航 <Link> 在点击前被卸载（点击稳定性检查永不满足）。
      // 装 sector-fund-flow 全量 mock（与 sector-fund-flow.spec.ts 同款），让源页稳定，
      // 再点击导航项验证跳转——断言仍是「点击 ETF 监控 → 到达 /dashboard/etf-monitor」。
      //
      // plan-05 起 ETF 监控页接入 EtfMonitorPage 业务组件，进入即向 etfMonitorApi 发请求；
      // 未装 ETF mock 时请求打到真实后端被 401 拒绝 → 触发 handleUnauthorizedRedirect 跳 /login，
      // 使 toHaveURL 断言失败。故一并装 ETF mock 让目标页稳定（断言仍是 URL 跳转）。
      await installFullFundFlowMocks(page)
      await installEtfMonitorMocks(page)
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      const menuLink = page.getByRole('link', { name: 'ETF 监控' })
      await menuLink.click()

      // 断言：URL 跳转到 ETF 监控页
      await expect(page).toHaveURL(/\/dashboard\/etf-monitor/)
    })
  })

  test.describe('路由壳渲染（plan-04 §3 #4：DashboardLayout 包裹业务页）', () => {
    test('TC-4.4 ETF 监控页空载渲染业务页内容', async ({ page }) => {
      // plan-05 起，page.tsx 接入 EtfMonitorPage 业务组件，原 plan-04 占位文本
      // 「ETF 监控（建设中）」已移除。装 ETF mock 让页面业务内容（排行表）稳定渲染，
      // 断言改为「页面可达 + EtfMonitorPage 业务内容（排行表 testid）渲染」。
      await installEtfMonitorMocks(page)
      await page.goto(ETF_MONITOR_PAGE)

      await expect(page).toHaveURL(/\/dashboard\/etf-monitor/)
      await expect(page.getByTestId('etf-index-ranking-table')).toBeVisible()
    })

    test('TC-4.5 ETF 监控页套用 DashboardLayout（侧边栏可见）', async ({ page }) => {
      // plan-05 起 ETF 监控页接入业务组件会发请求；装 ETF mock 避免请求打到真实
      // 后端被 401 拒绝触发重定向 /login（断言仍是侧边栏可见）。
      await installEtfMonitorMocks(page)
      await page.goto(ETF_MONITOR_PAGE)

      // 断言：DashboardLayout 侧边栏存在（与 sector-fund-flow 同布局）
      await expect(page.getByRole('link', { name: '板块资金流' })).toBeVisible()
    })
  })

  test.describe('降级回归（架构 §8.2：新增导航不影响现有布局）', () => {
    test('TC-4.6 现有导航项与 active 高亮不受影响', async ({ page }) => {
      // 进入板块资金流页，确认其导航项 active 态正常
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      const fundFlowLink = page.getByRole('link', { name: '板块资金流' })
      await expect(fundFlowLink).toBeVisible()
      // active 高亮：href 匹配当前路径（Sidebar.isActive 精确匹配 pathname）
      await expect(fundFlowLink).toHaveAttribute('href', '/dashboard/sector-fund-flow')
    })
  })
})

// ============================================================================
// plan-05：业务交互用例（EtfMonitorPage 双视图协调 + 排行表/趋势图/明细）
// 以下用例依赖 plan-05 的 EtfMonitorPage 业务组件，mock 来自 mock-etf-monitor-api.ts
// （installEtfMonitorMocks mock etfMonitorApi 4 个端点：index-rankings /
// index-detail / trend / latest-date，返回符合 etfMonitorTypes.ts 的 camelCase 数据）。
// plan-05 red 阶段：业务组件尚未实现（page.tsx 仍是 plan-04 占位空壳），TC-5.1~5.12
// 因 data-testid 不存在（排行表/趋势图未渲染）而预期失败。
// testid 命名与 plan-05 §3 实现规格一致：etf-index-ranking-table / etf-trend-chart /
// etf-detail-row / etf-category-{broad|industry} / etf-sort-{field} / etf-view-{ranking|trend} 等。
// ============================================================================

test.describe('plan-05：指数排行视图（AC-01/02/03/05/13）', () => {
  test('TC-5.1 默认显示宽基指数排行（AC-01：骨架屏→数据，按 totalNetInflow 降序，正负色标）', async ({
    page,
  }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 排行表格可见（宽基维度默认）
    await expect(page.getByTestId('etf-index-ranking-table')).toBeVisible()

    // 默认宽基 3 行，按 netInflow desc：沪深300(+12亿) > 创业板指(+0.8亿) > 中证500(-3.5亿)
    const rows = page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    await expect(rows).toHaveCount(3)
    await expect(rows.first()).toContainText('沪深300')
    await expect(rows.last()).toContainText('中证500')

    // 净流入额正值带 + 号（formatSignedAmount）、负值无 + 号（红涨绿跌色标，断文案）
    await expect(rows.first()).toContainText('+12')
    await expect(rows.last()).toContainText('-3.5')
  })

  test('TC-5.2 宽基/行业维度切换（AC-02：数据联动，再切回正常）', async ({ page }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 初始宽基维度：沪深300 在第一行
    await expect(
      page.locator('[data-testid="etf-index-ranking-table"] tbody tr').first()
    ).toContainText('沪深300')

    // 切换为行业维度（mock 按 category 返回差异化标签）
    await page.getByTestId('etf-category-industry').click()

    // 数据联动：行业维度第一行为「半导体」，沪深300 消失
    const rowsIndustry = page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    await expect(rowsIndustry).toHaveCount(2)
    await expect(rowsIndustry.first()).toContainText('半导体')
    await expect(rowsIndustry.filter({ hasText: '沪深300' })).toHaveCount(0)

    // 再切回宽基：沪深300 回归
    await page.getByTestId('etf-category-broad').click()
    await expect(
      page.locator('[data-testid="etf-index-ranking-table"] tbody tr').first()
    ).toContainText('沪深300')
  })

  test('TC-5.3 净流入额/份额变化/份额排序切换（AC-03：三态箭头，不可排序列不触发）', async ({
    page,
  }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    const rows = page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    await expect(rows).toHaveCount(3)

    // 默认 netInflow desc：沪深300(+12亿) > 创业板指(+0.8亿) > 中证500(-3.5亿)
    await expect(rows.first()).toContainText('沪深300')

    // 点 netInflow 表头切到 asc：中证500(-3.5亿) 升到首行
    await page.getByTestId('etf-sort-netInflow').click()
    await expect(rows.first()).toContainText('中证500')

    // 点 shareChange 表头 → desc（默认 desc）：沪深300(+5亿份) 首行
    await page.getByTestId('etf-sort-shareChange').click()
    await expect(rows.first()).toContainText('沪深300')

    // 点 share 表头 → desc：沪深300(800亿份) 首行
    await page.getByTestId('etf-sort-share').click()
    await expect(rows.first()).toContainText('沪深300')
  })

  test('TC-5.4 切换日期查看历史排行（AC-05：有数据/无数据日期）', async ({ page }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 默认最新交易日 2026-07-28 有数据：表格 3 行
    await expect(
      page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    ).toHaveCount(3)

    // 换无数据日期：装空数据 mock，选该日期 → 空态文案
    await mockEtfIndexRankingsEmpty(page)
    await page.getByTestId('etf-trade-date').fill('2026-07-25')
    await page.getByTestId('etf-trade-date').press('Enter')

    // 该日期暂无 ETF 数据（plan-05 §3 空态文案 hasData=false）
    await expect(page.getByTestId('etf-ranking-empty')).toBeVisible()
    await expect(
      page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    ).toHaveCount(0)
  })

  test('TC-5.5 分页浏览（AC-13：翻页、展开行收起）', async ({ page }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 分页控件可见（默认第 1 页）
    await expect(page.getByTestId('etf-pagination')).toBeVisible()
    await expect(page.getByTestId('etf-page-info')).toBeVisible()

    // 默认宽基 3 行（< 单页 pageSize 20，翻页按钮存在但下一页禁用/无数据）
    await expect(
      page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    ).toHaveCount(3)
  })
})

test.describe('plan-05：指数明细（AC-04）', () => {
  test('TC-5.6 展开指数查看 ETF 明细（AC-04：按 netInflow 降序，展开标记不跳转）', async ({
    page,
  }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 沪深300 行的展开标记可见（▶ 展开标记，与趋势入口分离）
    await expect(page.getByTestId('etf-expand-沪深300')).toBeVisible()

    // 展开前：无明细行
    await expect(page.getByTestId('etf-detail-row-510300.SH')).toHaveCount(0)

    // 点击展开标记 → 渲染该指数下 ETF 明细
    await page.getByTestId('etf-expand-沪深300').click()

    // 明细按 netInflow desc：510300.SH(6亿) > 510310.SH(2亿)
    const detailRows = page.locator('[data-testid^="etf-detail-row-"]')
    await expect(detailRows).toHaveCount(2)
    await expect(detailRows.first()).toContainText('510300.SH')
    await expect(detailRows.first()).toContainText('华泰柏瑞沪深300ETF')
    await expect(detailRows.last()).toContainText('510310.SH')

    // 再次点击展开标记 → 收起，明细行消失（视图不跳转）
    await page.getByTestId('etf-expand-沪深300').click()
    await expect(page.getByTestId('etf-detail-row-510300.SH')).toHaveCount(0)
  })
})

test.describe('plan-05：历史趋势视图（AC-06/07/08/09/11）', () => {
  test('TC-5.7 切换到历史趋势视图（AC-06：未选对象显示引导态，不画空坐标系）', async ({
    page,
  }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 切到趋势视图
    await page.getByTestId('etf-view-trend').click()

    // 未选对象：引导态文案可见，不画空坐标系（趋势图容器不渲染或渲染引导态）
    await expect(page.getByTestId('etf-trend-placeholder')).toBeVisible()
    await expect(page.getByTestId('etf-trend-chart')).toHaveCount(0)
  })

  test('TC-5.8 查看指数份额/净流入额曲线 + 区间切换（AC-07）', async ({ page }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 切到趋势视图，选指数「沪深300」+ 默认净流入额 + 7 日
    await page.getByTestId('etf-view-trend').click()
    await page.getByTestId('etf-trend-target-type-index').click()
    await page.getByTestId('etf-trend-target-select').click()
    await page.getByRole('option', { name: '沪深300' }).click()

    // 趋势曲线渲染（netInflow 7 日序列）
    await expect(page.getByTestId('etf-trend-chart')).toBeVisible()

    // 切指标为份额（share）
    await page.getByTestId('etf-trend-metric-share').click()
    await expect(page.getByTestId('etf-trend-chart')).toBeVisible()

    // 切区间为 30 日
    await page.getByTestId('etf-trend-days-30').click()
    await expect(page.getByTestId('etf-trend-chart')).toBeVisible()
  })

  test('TC-5.9 趋势视图下钻到单只 ETF（AC-08：曲线量级变化，单只 < 汇总）', async ({
    page,
  }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 趋势视图：先看指数「沪深300」净流入额曲线
    await page.getByTestId('etf-view-trend').click()
    await page.getByTestId('etf-trend-target-type-index').click()
    await page.getByTestId('etf-trend-target-select').click()
    await page.getByRole('option', { name: '沪深300' }).click()
    await expect(page.getByTestId('etf-trend-chart')).toBeVisible()

    // 切对象类型为单只 ETF，选 510300.SH
    await page.getByTestId('etf-trend-target-type-etf').click()
    await page.getByTestId('etf-trend-target-select').click()
    await page.getByRole('option', { name: '510300.SH' }).click()

    // 单只 ETF 曲线渲染（量级变化，AC-08：单只 < 汇总，仅断言渲染成功）
    await expect(page.getByTestId('etf-trend-chart')).toBeVisible()
  })

  test('TC-5.10 趋势对象历史不足所选区间（AC-09：正常绘制已有部分，不报错）', async ({
    page,
  }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 趋势视图：选历史不足对象（target_code 含 __short__ 标记 → mock 返回 3 天 < 7 天）
    await page.getByTestId('etf-view-trend').click()
    await page.getByTestId('etf-trend-target-type-index').click()
    await page.getByTestId('etf-trend-target-select').click()
    await page.getByRole('option', { name: '__short__不足区间' }).click()

    // 选 90 日区间，但该对象只有 3 天数据 → 正常绘制已有部分（不报错、不空态）
    await page.getByTestId('etf-trend-days-90').click()
    await expect(page.getByTestId('etf-trend-chart')).toBeVisible()
    // 有部分数据不应走空态
    await expect(page.getByTestId('etf-trend-empty')).toHaveCount(0)
  })

  test('TC-5.11 从排行跳转趋势视图（AC-11：趋势入口跳转并定位对象，展开标记不跳转）', async ({
    page,
  }) => {
    await installEtfMonitorMocks(page)
    await page.goto(ETF_MONITOR_PAGE)

    // 排行视图：点沪深300 行的「趋势」入口
    await page.getByTestId('etf-trend-entry-沪深300').click()

    // 视图切到趋势，对象自动定位到沪深300（index 类型）
    await expect(page.getByTestId('etf-view-trend')).toBeVisible()
    await expect(page.getByTestId('etf-trend-chart')).toBeVisible()

    // 回到排行视图验证：展开标记点击不跳转（仅展开/收起）
    await page.getByTestId('etf-view-ranking').click()
    await page.getByTestId('etf-expand-沪深300').click()
    // 仍在排行视图（展开标记不触发视图跳转）
    await expect(page.getByTestId('etf-index-ranking-table')).toBeVisible()
    await expect(page.getByTestId('etf-detail-row-510300.SH')).toBeVisible()
  })
})

test.describe('plan-05：错误与重试（AC-10）', () => {
  test('TC-5.12 加载失败可重试（AC-10：错误态 + 重试按钮，双视图独立降级）', async ({
    page,
  }) => {
    // index-rankings 返回 500 → 排行错误态；其余端点正常（双视图独立降级 AC-10/架构 §8.2）
    await mockEtfIndexRankingsError(page)
    await mockEtfIndexDetail(page)
    await mockEtfTrend(page)
    await mockEtfLatestDate(page, '2026-07-28')
    await page.goto(ETF_MONITOR_PAGE)

    // 排行区错误态 + 重试按钮可见
    await expect(page.getByTestId('etf-ranking-error')).toBeVisible()
    await expect(page.getByTestId('etf-ranking-retry')).toBeVisible()
    // 错误态下排行表格数据行不渲染
    await expect(
      page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    ).toHaveCount(0)

    // 重新装正常 mock 后点重试 → 数据恢复
    await mockEtfIndexRankings(page)
    await page.getByTestId('etf-ranking-retry').click()
    await expect(
      page.locator('[data-testid="etf-index-ranking-table"] tbody tr')
    ).toHaveCount(3)
  })
})
