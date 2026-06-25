import { test as base, expect, type Page } from '@playwright/test'
import {
  mockCrowdRankings,
  mockCrowdRankingsEmpty,
  mockCrowdIndustryDistribution,
  mockCrowdIndustryDistributionEmpty,
  createTestCrowdRankings,
  createTestCrowdIndustryDistribution,
} from './helpers/mock-fund-crowd-api'
import { mockReverseLookup, createTestReverseLookup } from './helpers/mock-fund-api'

const FUND_CROWD_ANALYSIS_PAGE = '/dashboard/fund-crowd-analysis'

/**
 * 扩展 test fixture：在每个测试前注入普通用户认证
 *
 * 参照 shareholder-analysis.spec.ts:22-53 模式：本项目使用自定义
 * JWT（token 存 localStorage + Cookie access_token），非 NextAuth。
 *
 * plan-02 是面向普通登录用户的页面（非管理员路由），role 设为 user 即可
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
 * 安装默认全量 mock（rankings + industry-distribution）
 * 用于多数 Happy 场景
 */
async function installFullMocks(
  page: Page,
  opts?: { hasPrevPeriod?: boolean }
): Promise<void> {
  await mockCrowdRankings(page, createTestCrowdRankings({ hasPrevPeriod: opts?.hasPrevPeriod ?? true }))
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistribution())
  // plan-03 TC-3.4 跳转 04 反查页需 mock reverse-lookup，否则 API 无 mock → 401 → 重定向 /login
  await mockReverseLookup(page, createTestReverseLookup())
}

// 给等待搜索 debounce 预留 buffer（300ms debounce + 网络 mock 响应，规则 5 race 规避）
const SEARCH_DEBOUNCE_BUFFER = 500

test.describe('AC-01/02/03/04/06/07/08：基金扎堆分析页（plan-02）', () => {
  test.describe('排行榜展示（AC-01）', () => {
    test('TC-2.1 进入页面默认展示仅主动基金扎堆度排行榜', async ({ page }) => {
      await installFullMocks(page, { hasPrevPeriod: true })
      await page.goto(FUND_CROWD_ANALYSIS_PAGE)

      // 默认「仅主动基金」选中（规则 7：用 aria-pressed 而非文案做等待/断言）
      await expect(page.getByTestId('crowd-scope-active')).toHaveAttribute('aria-pressed', 'true')

      // 排行榜表格可见，按基金数降序（286 > 198 > 45）
      const rows = page.locator('[data-testid="crowd-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)
      await expect(rows.first()).toContainText('600519')
      await expect(rows.first()).toContainText('286')
      await expect(rows.nth(1)).toContainText('300750')
      await expect(rows.nth(1)).toContainText('198')
      await expect(rows.nth(2)).toContainText('688981')
    })
  })

  test.describe('口径切换（AC-02）', () => {
    test('TC-2.2 切换口径为全部基金后排行榜重新计算', async ({ page }) => {
      await installFullMocks(page, { hasPrevPeriod: true })
      await page.goto(FUND_CROWD_ANALYSIS_PAGE)

      // 初始：600519 基金数 286
      await expect(
        page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()
      ).toContainText('286')

      // 切换为全部基金（mock 内 scope=all 时 fundCount 翻倍）
      await page.getByTestId('crowd-scope-all').click()
      await expect(page.getByTestId('crowd-scope-all')).toHaveAttribute('aria-pressed', 'true')
      await expect(page.getByTestId('crowd-scope-active')).toHaveAttribute('aria-pressed', 'false')
      await expect(
        page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()
      ).toContainText('572')

      // 切回仅主动
      await page.getByTestId('crowd-scope-active').click()
      await expect(page.getByTestId('crowd-scope-active')).toHaveAttribute('aria-pressed', 'true')
      await expect(
        page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()
      ).toContainText('286')
    })
  })

  test.describe('环比变化与新进标识（AC-03）', () => {
    test('TC-2.3 环比变化列展示升降数值与新进标识', async ({ page }) => {
      await installFullMocks(page, { hasPrevPeriod: true })
      await page.goto(FUND_CROWD_ANALYSIS_PAGE)

      const rows = page.locator('[data-testid="crowd-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)

      // 600519：基金 +12（抱团加强，绿色 ↑）
      const row1 = rows.first()
      await expect(row1).toContainText('600519')
      await expect(row1).toContainText(/基金\s*\+12/)

      // 300750：基金 -8（抱团瓦解，红色 ↓）
      const row2 = rows.nth(1)
      await expect(row2).toContainText('300750')
      await expect(row2).toContainText(/基金\s*-8/)

      // 688981：新进标识（AC-03）—— 用 data-testid 精确定位（规则 5/7）
      await expect(page.getByTestId('crowd-new-badge-688981')).toBeVisible()
    })
  })

  test.describe('行业分布（AC-04）', () => {
    test('TC-2.4 行业分布按扎堆股数量占比展示', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(FUND_CROWD_ANALYSIS_PAGE)

      // 行业分布区可见（规则 7：用 data-testid 等待，不依赖文案）
      await expect(page.getByTestId('crowd-industry-distribution')).toBeVisible()

      // 双轨标签解法（参照 06 IndustryDistribution）：
      //   ECharts canvas 点击不稳定，canvas 旁渲染可点击 DOM button，spec 用 getByTestId
      // 食品饮料（占比最高 16.0%）
      await expect(page.getByTestId('crowd-industry-bar-食品饮料')).toBeVisible()
      await expect(page.getByTestId('crowd-industry-bar-食品饮料')).toContainText('16.0%')
      // 其他行业标签
      await expect(page.getByTestId('crowd-industry-bar-电力设备')).toBeVisible()
      await expect(page.getByTestId('crowd-industry-bar-银行')).toBeVisible()
    })
  })

  test.describe('上期数据缺失降级（AC-06）', () => {
    test('TC-2.5 上期数据缺失时环比列显示占位符', async ({ page }) => {
      await installFullMocks(page, { hasPrevPeriod: false })
      await page.goto(FUND_CROWD_ANALYSIS_PAGE)

      const rows = page.locator('[data-testid="crowd-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)

      // AC-06：所有行不显示新进标识（hasPrevPeriod=false 时 isNew=null）
      await expect(page.getByTestId('crowd-new-badge-688981')).toHaveCount(0)

      // 每行的环比列含 "—"（用容器限定，规则 5 避免 getByText 多匹配）
      for (let i = 0; i < 3; i++) {
        // 环比列标识：用 row 内 data-testid 限定到 change 单元格
        const changeCell = rows.nth(i).locator('[data-testid^="crowd-change-cell-"]')
        await expect(changeCell).toContainText('—')
      }
    })
  })

  test.describe('持仓数据未同步空状态（AC-07）', () => {
    test('TC-2.6 持仓数据未同步展示整页空状态', async ({ page }) => {
      await mockCrowdRankingsEmpty(page)
      await mockCrowdIndustryDistributionEmpty(page)
      await page.goto(FUND_CROWD_ANALYSIS_PAGE)

      // 整页空状态（规则 7：用 data-testid 等待）
      await expect(page.getByTestId('crowd-empty-portfolio')).toBeVisible()
      // 文案断言（可依赖文案做断言，不做等待）
      await expect(page.getByText('暂无基金持仓数据', { exact: false })).toBeVisible()

      // 不渲染排行榜与行业分布
      await expect(page.getByTestId('crowd-ranking-table')).toHaveCount(0)
      await expect(page.getByTestId('crowd-industry-distribution')).toHaveCount(0)
    })
  })

  test.describe('搜索过滤（AC-08）', () => {
    test('TC-2.7 搜索过滤、无结果提示与清空恢复', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(FUND_CROWD_ANALYSIS_PAGE)

      // 等待表格加载完成（3 行）
      const rows = page.locator('[data-testid="crowd-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)

      // 输入代码前缀 "600" → 仅命中 600519
      await page.getByTestId('crowd-search-input').fill('600')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(1)
      await expect(rows.first()).toContainText('600519')

      // 输入名称包含 "茅台" → 仅命中 600519
      await page.getByTestId('crowd-search-input').fill('茅台')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(1)
      await expect(rows.first()).toContainText('600519')

      // 输入无匹配词 → 无结果提示
      await page.getByTestId('crowd-search-input').fill('不存在的股票')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(page.getByText('未找到匹配股票', { exact: false })).toBeVisible()

      // 清空 → 恢复完整榜单（3 条）
      await page.getByTestId('crowd-search-clear').click()
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(3)
    })
  })
})

// ============================================================================
// plan-03 / AC-05：下钻反查跳转 + 返回状态恢复（扎堆分析页侧）
// 2 个场景：反查按钮点击跳转 04 反查页 / 返回后口径页码搜索 scroll 恢复
// 复用 plan-02 的 authedPage fixture + installFullMocks + RETURN_STATE_STORAGE_KEY 约定
// ============================================================================

test.describe('AC-05：下钻反查跳转 + 返回状态恢复（plan-03）', () => {
  test('TC-3.4 点击反查按钮跳转 04 反查页（带 symbol + from=fund-crowd）', async ({ page }) => {
    await installFullMocks(page, { hasPrevPeriod: true })
    await page.goto(FUND_CROWD_ANALYSIS_PAGE)

    // 等待表格加载完成（3 行）
    const rows = page.locator('[data-testid="crowd-ranking-table"] tbody tr')
    await expect(rows).toHaveCount(3)

    // 点击第一行（600519）的反查按钮（plan-02 已渲染 testid；plan-03 在 handleReverseLookup wire 路由跳转）
    await rows.first().getByTestId('crowd-reverse-lookup-600519').click()

    // 断言：路由跳转到 04 反查页，URL 含 symbol=600519 + from=fund-crowd
    await expect(page).toHaveURL(
      /\/dashboard\/funds\/reverse-lookup\?symbol=600519&from=fund-crowd/
    )
  })

  test('TC-3.5 返回后恢复原口径/页码/搜索/滚动位置', async ({ page }) => {
    await installFullMocks(page, { hasPrevPeriod: true })

    // 模拟 plan-03 写入的 sessionStorage（从 04 反查页点击「返回扎堆分析」时的状态）
    // sessionStorage 跨路由同源同标签页保留；用 addInitScript 在 page 加载前注入
    //
    // scrollY=50：在 search='600' 过滤后（1 行结果）<main> 的 maxScroll≈99，故 50 是稳定可达的目标值。
    // 断言保留严格容差 error < 50（恢复后 main.scrollTop 必须落在 [1, 99]，证明 scroll 真实恢复）。
    await page.addInitScript(() => {
      sessionStorage.setItem(
        'fund-crowd-return-state',
        JSON.stringify({
          scope: 'all', // 切换为全部基金口径
          page: 1,
          search: '600', // 搜索词
          scrollX: 0,
          scrollY: 50, // 滚动位置（AC-05 非阻塞改进项）
        })
      )
    })

    await page.goto(FUND_CROWD_ANALYSIS_PAGE)

    // 断言：口径恢复为「全部基金」（plan-02 已实现基础 scope 恢复）
    await expect(page.getByTestId('crowd-scope-all')).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    // 断言：搜索词恢复（plan-02 已实现基础 search 恢复 + 同步 debouncedSearch）
    await expect(page.getByTestId('crowd-search-input')).toHaveValue('600')

    // 断言：sessionStorage 已被消费清空（一次性消费，避免刷新误恢复）
    const remaining = await page.evaluate(() =>
      sessionStorage.getItem('fund-crowd-return-state')
    )
    expect(remaining).toBeNull()

    // 断言：scroll 恢复（plan-03 Task 5 新增；非阻塞改进项，允许 ±50px 误差）
    // 等待数据加载 + DOM 渲染稳定（plan-03 用 requestAnimationFrame + setTimeout(0) 时机恢复，
    // 且监听 rankings 加载完成后才触发；数据 mock 即时返回时通常 < 300ms 内恢复到位）
    //
    // 注意：实际滚动发生在 DashboardLayout 的 <main> 容器（root h-screen overflow-hidden，
    // main flex-1 overflow-y-auto），window.scrollY 在本布局下始终为 0。故断言目标是
    // document.querySelector('main').scrollTop（与实现 handleReverseLookup/恢复 useEffect 一致）。
    await page.waitForTimeout(500)
    const scrollY = await page.evaluate(
      () => document.querySelector('main')?.scrollTop ?? 0
    )
    expect(Math.abs(scrollY - 50)).toBeLessThan(50)
  })
})
