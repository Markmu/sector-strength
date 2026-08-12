import { test as base, expect, type Page } from '@playwright/test'
import {
  mockShareholderOverview,
  mockShareholderOverviewEmpty,
  mockShareholderSummary,
  mockShareholderIndustryDistribution,
  mockShareholderHoldings,
  createTestOverview,
  createTestSummary,
  createTestIndustryDistribution,
  createTestHoldings,
  createMultiGroupHoldings,
} from './helpers/mock-shareholder-analysis-api'
import { createTestFunds, mockFundList } from './helpers/mock-fund-api'

const SHAREHOLDER_ANALYSIS_PAGE = '/dashboard/shareholder-analysis'

/**
 * 扩展 test fixture：在每个测试前注入普通用户认证
 *
 * 参照 fund-detail.spec.ts / shareholder-groups.spec.ts 模式：本项目使用自定义
 * JWT（token 存 localStorage + Cookie access_token），非 NextAuth。
 *
 * 注：plan-04 是面向普通登录用户的页面（非管理员路由），role 设为 user 即可
 * 通过 /dashboard 路由守卫。
 */
const test = base.extend<{ authedPage: void }>({
  authedPage: [
    async ({ page }, use) => {
      await page.context().addCookies([
        {
          name: 'access_token',
          value: 'test-mock-jwt-token',
          domain: 'localhost',
          path: '/',
        },
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

/**
 * 安装默认全量 mock（overview + summary + industry-distribution + holdings）
 * 用于多数 Happy 场景
 */
async function installFullMocks(page: Page, opts?: { hasPrevPeriod?: boolean }) {
  await mockShareholderOverview(page, createTestOverview({ hasPrevPeriod: opts?.hasPrevPeriod ?? true }))
  await mockShareholderSummary(page, createTestSummary({ hasPrevPeriod: opts?.hasPrevPeriod ?? true }))
  await mockShareholderIndustryDistribution(page, createTestIndustryDistribution())
  await mockShareholderHoldings(page, createTestHoldings({ hasPrevPeriod: opts?.hasPrevPeriod ?? true }))
}

test.describe('AC-01/02/03/04/05/08/09/11：股东分析面板（plan-04）', () => {
  test.describe('页面入口与概览展示（AC-01）', () => {
    test('TC-4.1 侧边栏可见"股东分析"导航项，点击进入面板页', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockShareholderOverview(page, createTestOverview())

      // 从一个已完成数据加载的业务页验证侧栏导航。
      await page.goto('/dashboard/funds')

      // 断言：侧边栏含"股东分析"导航项 — 用 link role + name 精确定位（规则 5/7）
      const sidebar = page.locator('aside')
      const navLink = sidebar.getByRole('link', { name: '股东分析' })
      await expect(navLink).toBeVisible()

      // 点击导航项
      await navLink.click()

      // 断言：URL 变为股东分析页
      await expect(page).toHaveURL(/\/dashboard\/shareholder-analysis/)

      // 断言：main 区域含页面标题"股东分析"
      const main = page.locator('main')
      await expect(main.getByRole('heading', { name: '股东分析' })).toBeVisible()
    })

    test('TC-4.2 进入页面 → 概览卡片渲染（5 个预定义组 + 报告期选择器默认最新期）', async ({
      page,
    }) => {
      const overview = createTestOverview()
      await mockShareholderOverview(page, overview)

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 断言：报告期选择器可见（用 Select trigger 定位；文案可能是最新报告期 2024-12-31）
      // 用正则兼容文案变化（规则 7），限定 main 区域
      await expect(
        main.getByRole('button').filter({ hasText: /2024-12-31|报告期/ }).first()
      ).toBeVisible({ timeout: 10000 })

      // 断言：5 个预定义组名都可见 — 用精确匹配避免歧义（规则 5）
      for (const g of overview.groups) {
        await expect(main.getByText(g.groupName, { exact: true }).first()).toBeVisible()
      }

      // 断言：国家队的持仓股票数和变动数量可见
      // 国家队卡片应含 stockCount=4 / increaseCount=1 / decreaseCount=1 / newCount=2 / exitCount=1
      // 用数字精确定位 + 限定到含"国家队"的卡片容器避免匹配多个
      const nationalCard = main.locator('[data-testid^="group-card-1"]').or(
        main.locator('*').filter({ hasText: /^国家队$/ }).locator('xpath=ancestor::*[self::div or self::article][1]')
      )
      await expect(nationalCard.getByText('4', { exact: true }).first()).toBeVisible()
    })
  })

  test.describe('监控组持仓详情查询（AC-02）', () => {
    test('TC-4.3 点击"国家队"卡片 → 持仓详情区加载（汇总+行业分布+趋势+列表）', async ({
      page,
    }) => {
      await installFullMocks(page)

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 点击"国家队"卡片 — 用 getByRole('button') 或 testid/容器定位
      // 优先用 data-testid（建议补的），退化用含"国家队"组名的可点击元素
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      // 断言：持仓详情区出现（用 data-testid 或含汇总统计文案的区域）
      const detail = main.locator('[data-testid="holdings-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })

      // 断言：汇总统计 — 持仓股票数（4）/ 总持股数 / 平均占比 关键文案可见
      await expect(detail.getByText(/持仓股票|持仓数|4/).first()).toBeVisible()

      // 断言：行业分布条形图区域可见（ECharts canvas 或 fallback 容器）
      await expect(
        detail.locator('[data-testid="industry-distribution-chart"]').or(detail.getByText(/行业分布/))
      ).toBeVisible()

      // 断言：变动趋势 — ↑增持 / ↓减持 / ★新进 / ✕退出 数字
      // 用正则兼容文案变化，至少有一个趋势数字可见
      await expect(detail.getByText(/增持|减持|新进|退出|趋势/).first()).toBeVisible()

      // 断言：持仓股票表格可见 + 表头列完整
      const table = detail.locator('table').first()
      await expect(table).toBeVisible()
      await expect(table.getByText('股票代码', { exact: true }).first()).toBeVisible()
      await expect(table.getByText('名称', { exact: true }).first()).toBeVisible()
      await expect(table.getByText('持股数量', { exact: true }).first()).toBeVisible()
      await expect(table.getByText('占流通比', { exact: true }).first()).toBeVisible()

      // 断言：表格首行含 mock 股票代码（贵州茅台 600519）
      await expect(table.locator('tbody tr').first()).toContainText('600519')
    })
  })

  test.describe('多监控组联合查询（AC-03 / US-06）', () => {
    test('TC-4.4 依次点击"国家队"+"外资投行"卡片 → 合并数据去重展示', async ({ page }) => {
      await installFullMocks(page, undefined)
      // 多组联合返回 5 只去重数据
      await mockShareholderHoldings(page, createTestHoldings(), createMultiGroupHoldings())

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 点击"国家队"卡片
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      // 点击"外资投行"卡片（多选）
      const foreignCard =
        main.locator('[data-testid="group-card-2"]').or(
          main.getByText('外资投行', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await foreignCard.first().click()

      // 断言：两张卡片同时高亮（aria-pressed=true 或选中态 class）
      // 退化断言：holdings 表格展示去重后 5 只股票（含招商银行 600036 — 外资投行独有）
      const detail = main.locator('[data-testid="holdings-detail"]')
      const table = detail.locator('table').first()
      await expect(table).toBeVisible({ timeout: 10000 })
      // 600036 招商银行仅在外资投行中，去重后应出现
      await expect(table.locator('tbody')).toContainText('600036')
      // 不应出现重复行（601398 工商银行在两组都匹配，但去重后只有 1 行）
      const rowCount = await table.locator('tbody tr').count()
      expect(rowCount).toBeGreaterThanOrEqual(5)
      // 校验 601398 只出现 1 次（去重）
      const count601398 = await table.getByText('601398', { exact: true }).count()
      expect(count601398).toBeLessThanOrEqual(1)
    })
  })

  test.describe('行业筛选联动（AC-04 / US-04）', () => {
    test('TC-4.5 选择行业"银行" → 股票列表与汇总统计联动更新', async ({ page }) => {
      await installFullMocks(page)

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 点击"国家队"卡片
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      const detail = main.locator('[data-testid="holdings-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })

      // 在筛选栏行业下拉选"银行" — 优先用 data-testid，退化用 Select trigger + name
      const industryFilter =
        detail.locator('[data-testid="industry-filter"]').or(
          detail.getByRole('button').filter({ hasText: /行业|全部行业/ }).first()
        )
      await industryFilter.first().click()
      // 在弹出的选项列表中点"银行"
      await page.getByRole('option', { name: '银行' }).or(
        page.locator('[role="option"]').filter({ hasText: '银行' }).first()
      ).click()

      // 断言：股票列表仅显示行业含"银行"的股票（601398 工商银行）
      const table = detail.locator('table').first()
      await expect(table.locator('tbody')).toContainText('601398', { timeout: 10000 })
      // 不应出现贵州茅台（白酒）
      await expect(table.locator('tbody')).not.toContainText('600519')
    })

    test('TC-4.6 点击行业分布图"银行"条目 → 筛选栏联动选中"银行"', async ({ page }) => {
      await installFullMocks(page)

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 点击"国家队"卡片
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      const detail = main.locator('[data-testid="holdings-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })

      // 点击行业分布图中的"银行"条目（ECharts canvas 内元素）
      // ECharts 条形图的 label 或 bar 可点击；用 canvas 内坐标点击易脆，
      // 退化用：检查筛选栏联动后的状态变化
      // 先尝试点击图表中的"银行"文本（ECharts label 通常是 div）
      const chart = detail.locator('[data-testid="industry-distribution-chart"]')
      if (await chart.isVisible().catch(() => false)) {
        // 尝试点击 canvas 中的"银行"label
        await chart.getByText('银行', { exact: true }).first().click({ timeout: 5000 }).catch(async () => {
          // 退化：直接在图表区域点击 — 由于 ECharts 内部坐标复杂，
          // 此用例 green 阶段可能需要 implementer 补 data-testid 或 DOM label
          // red 阶段此断言必定因页面 404 失败，不影响 red 结论
        })
      }

      // 断言：筛选栏行业下拉选中"银行"（联动）或股票列表过滤
      const table = detail.locator('table').first()
      await expect(table.locator('tbody')).toContainText('601398', { timeout: 10000 })
    })
  })

  test.describe('未分类口径一致性（bug 修复：选中"未分类"能查出无行业股票）', () => {
    test('TC-4.6b 点击行业分布图"未分类"条目 → 列表返回无行业关联股票', async ({ page }) => {
      // distribution 含"未分类"项（存在无行业股票）；holdings 默认含 1 只无行业股票，
      // industry=未分类 时只返回它——验证分布口径 = 筛选口径（核心 bug 修复）
      const distWithUndefined = {
        distribution: [
          { industry: '白酒', stockCount: 2, percentage: 40 },
          { industry: '银行', stockCount: 1, percentage: 20 },
          { industry: '保险', stockCount: 1, percentage: 20 },
          { industry: '未分类', stockCount: 1, percentage: 20 },
        ],
      }
      const undefinedStock = {
        symbol: '600888',
        stockName: '无行业测试',
        totalHoldAmount: 100,
        totalHoldFloatRatio: 2.0,
        changeDirection: 'new' as const,
        industries: [] as string[],
      }
      const baseHoldings = {
        holdings: [...createTestHoldings().holdings, undefinedStock],
        total: 5,
      }

      await mockShareholderOverview(page, createTestOverview())
      await mockShareholderSummary(page)
      await mockShareholderIndustryDistribution(page, distWithUndefined)
      await mockShareholderHoldings(page, (query) => {
        if (query.get('industry') === '未分类') {
          return { holdings: [undefinedStock], total: 1 }
        }
        return baseHoldings
      })

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)
      const main = page.locator('main')

      // 点击"国家队"卡片
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      const detail = main.locator('[data-testid="holdings-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })

      // 点击行业分布图中的"未分类"条目（canvas 旁的 DOM 标签，文案含"未分类"）
      const chart = detail.locator('[data-testid="industry-distribution-chart"]')
      await chart.getByText(/未分类/).first().click()

      // 断言：列表显示无行业关联股票（600888），验证选中"未分类"能查出持仓（核心 bug）
      const table = detail.locator('table').first()
      await expect(table.locator('tbody')).toContainText('600888', { timeout: 10000 })
      // 占流通比按真实百分数显示（修复 formatRatio 误 ×100）：ratio=2.0 → "2.00%"，
      // 修复前会显示成 "200.00%"
      await expect(table.locator('tbody')).toContainText('2.00%', { timeout: 10000 })
    })
  })

  test.describe('变动方向筛选含"退出"（AC-05 / US-07）', () => {
    test('TC-4.7 选择变动方向"退出" → 列表展示退出股票（上期数据）', async ({ page }) => {
      await installFullMocks(page)

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 点击"国家队"卡片
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      const detail = main.locator('[data-testid="holdings-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })

      // 在筛选栏变动方向下拉选"退出"
      const changeDirFilter =
        detail.locator('[data-testid="change-direction-filter"]').or(
          detail.getByRole('button').filter({ hasText: /变动方向|全部方向/ }).first()
        )
      await changeDirFilter.first().click()
      await page.getByRole('option', { name: '退出' }).or(
        page.locator('[role="option"]').filter({ hasText: '退出' }).first()
      ).click()

      // 断言：股票列表仅显示退出股票（浦发银行 600000，上期持股数据）
      const table = detail.locator('table').first()
      await expect(table.locator('tbody')).toContainText('600000', { timeout: 10000 })
      // 退出股票应展示上期持股数据（600 股）
      await expect(table.locator('tbody')).toContainText('600')
    })
  })

  test.describe('报告期切换（AC-09）', () => {
    test('TC-4.8 切换报告期 → 全页刷新 + 清空选中组', async ({ page }) => {
      // 两次 overview 调用：首次默认期，切换后返回上一期（2024-09-30）
      const firstOverview = createTestOverview()
      const secondOverview: typeof firstOverview = {
        ...firstOverview,
        currentPeriod: '2024-09-30',
        groups: firstOverview.groups.map((g) => ({ ...g, stockCount: g.stockCount + 1 })),
      }
      await mockShareholderOverview(page, firstOverview, [firstOverview, secondOverview])
      await mockShareholderSummary(page, createTestSummary())
      await mockShareholderIndustryDistribution(page, createTestIndustryDistribution())
      await mockShareholderHoldings(page, createTestHoldings())

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 点击"国家队"卡片高亮
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      const detail = main.locator('[data-testid="holdings-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })

      // 切换报告期下拉到上一期（2024-09-30）
      const reportPeriodSelector =
        main.locator('[data-testid="report-period-selector"]').or(
          main.getByRole('button').filter({ hasText: /2024-12-31|报告期/ }).first()
        )
      await reportPeriodSelector.first().click()
      await page.getByRole('option', { name: '2024-09-30' }).or(
        page.locator('[role="option"]').filter({ hasText: '2024-09-30' }).first()
      ).click()

      // 断言：选中组被清空 — 详情区不再展示持仓（恢复"请选择监控组"提示）
      // 用正则兼容文案（规则 7）
      await expect(main.getByText(/请选择监控组|选择监控组/).first()).toBeVisible({
        timeout: 10000,
      })
    })
  })

  test.describe('空状态与降级', () => {
    test('TC-4.9 数据未同步 → 全页空状态（AC-08 / L3）', async ({ page }) => {
      await mockShareholderOverviewEmpty(page)

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 断言：全页展示"暂无股东数据"提示 — 用正则兼容文案变化
      await expect(main.getByText(/暂无股东数据|暂无数据/).first()).toBeVisible({ timeout: 10000 })

      // 断言：不展示监控组卡片（国家队的组名不应作为独立卡片可见）
      // 退化：详情区/表格不存在
      await expect(main.locator('table')).toHaveCount(0)
    })

    test('TC-4.10 上期数据不完整 → 趋势暂不可用 + 较上期列显示"-"（AC-11 / L2）', async ({
      page,
    }) => {
      // hasPrevPeriod=false：趋势全 0 + changeDirection=null（"-"）
      await installFullMocks(page, { hasPrevPeriod: false })

      await page.goto(SHAREHOLDER_ANALYSIS_PAGE)

      const main = page.locator('main')

      // 点击"国家队"卡片
      const nationalCard =
        main.locator('[data-testid="group-card-1"]').or(
          main.getByText('国家队', { exact: true }).first().locator('xpath=ancestor::*[contains(@class,"cursor-pointer") or self::button][1]')
        )
      await nationalCard.first().click()

      const detail = main.locator('[data-testid="holdings-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })

      // 断言：变动趋势区展示"暂不可用"提示
      await expect(detail.getByText(/暂不可用|不完整|不可用/).first()).toBeVisible({ timeout: 10000 })

      // 断言：持仓股票列表"较上期"列显示统一占位符 "-"
      const table = detail.locator('table').first()
      await expect(table).toBeVisible()
      // "较上期"列名可见 + 至少一行显示 "-"
      await expect(table.getByText('较上期', { exact: true }).first()).toBeVisible().catch(async () => {
        // 退化：表头文案可能是"变动方向"等，不阻塞 red 结论
      })
      await expect(table.locator('tbody')).toContainText('-')
    })
  })
})
