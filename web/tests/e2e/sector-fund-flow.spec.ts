import { test as base, expect, type Page } from '@playwright/test'
import {
  installFullFundFlowMocks,
  mockFundFlowRankings,
  mockFundFlowRankingsError,
  mockFundFlowTimeseries,
  mockFundFlowLatestDate,
  createTestFundFlowRankings,
  createTestFundFlowTimeseries,
} from './helpers/mock-sector-fund-flow-api'

const SECTOR_FUND_FLOW_PAGE = '/dashboard/sector-fund-flow'

/**
 * 扩展 test fixture：在每个测试前注入普通用户认证
 *
 * 参照 fund-crowd-analysis.spec.ts:22-53 模式：本项目使用自定义
 * JWT（token 存 localStorage + Cookie access_token），非 NextAuth。
 *
 * plan-03 是面向普通登录用户的页面（非管理员路由），role 设为 user 即可
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
 * 安装默认全量 mock（rankings + timeseries + latest-date）
 * 用于多数 Happy 场景（AC-01/02/03/05/06/07）
 */
async function installFullMocks(page: Page): Promise<void> {
  await installFullFundFlowMocks(page)
}

test.describe('板块资金流页（plan-03，AC-01~AC-09）', () => {
  test.describe('资金流排行默认视图（AC-01/AC-02）', () => {
    test('TC1 进入页面默认显示排行视图（行业维度），表格可见', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 默认排行视图选中（规则 7：用 aria-selected 做等待/断言）
      await expect(page.getByTestId('fund-flow-view-ranking')).toHaveAttribute(
        'aria-selected',
        'true'
      )

      // 默认维度为「行业」：sector-type 按钮无 aria 属性（仅 class 区分激活态），
      // 用表格首行为行业维度数据「半导体」佐证默认维度
      await expect(
        page.locator('[data-testid="fund-flow-ranking-table"] tbody tr').first()
      ).toContainText('半导体')

      // 排行表格可见，默认按净额降序（半导体 12亿 > 银行 0.8亿 > 证券 -3.5亿）
      const rows = page.locator('[data-testid="fund-flow-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)
      await expect(rows.first()).toContainText('半导体')
      // 净额正值带 + 号（formatSignedAmount：12亿 → +12.00亿）
      await expect(rows.first()).toContainText('+12.00亿')
      await expect(rows.nth(1)).toContainText('银行')
      await expect(rows.nth(2)).toContainText('证券')
      // 证券净流出为负（无 + 号前缀，红色为正/绿色为负，这里只断文案）
      await expect(rows.nth(2)).toContainText('-3.50亿')

      // 净额排序表头处于激活态（▼ 降序）
      await expect(page.getByTestId('fund-flow-sort-net_inflow')).toContainText('净额')
    })
  })

  test.describe('维度切换（AC-02）', () => {
    test('TC2 切换到概念维度，表格数据联动', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 初始行业维度：半导体 在第一行
      await expect(
        page.locator('[data-testid="fund-flow-ranking-table"] tbody tr').first()
      ).toContainText('半导体')

      // 切换为概念维度（mock 按 sector_type 返回差异化标签）
      // sector-type 按钮无 aria 属性（仅 class 区分激活态），用数据联动佐证切换生效
      await page.getByTestId('fund-flow-sector-type-concept').click()

      // 数据联动：概念维度第一行为「新能源」（mock concept 首项），半导体消失
      const rows = page.locator('[data-testid="fund-flow-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(2)
      await expect(rows.first()).toContainText('新能源')
      await expect(rows.first()).toContainText('+8.00亿')
      // 概念维度 sectorId=null → 板块名不可点击（无 fund-flow-sector-link- 按钮）
      await expect(page.getByTestId('fund-flow-sector-link-新能源')).toHaveCount(0)
    })
  })

  test.describe('排序切换（AC-03）', () => {
    test('TC3 点击流入表头切换排序（desc → asc）', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 等待表格加载（3 行，行业维度）
      const rows = page.locator('[data-testid="fund-flow-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)

      // 默认净额降序：半导体(12亿) > 银行(0.8亿) > 证券(-3.5亿)
      await expect(rows.first()).toContainText('半导体')

      // 点击「流入」表头 → 切到 inflow 默认 desc
      // 行业流入额：半导体15亿 > 银行5亿 > 证券4亿 → desc 首行仍为半导体
      await page.getByTestId('fund-flow-sort-inflow').click()
      await expect(rows.first()).toContainText('半导体')

      // 再点一次「流入」→ 切到 asc（4亿 < 5亿 < 15亿 → 首行为证券）
      await page.getByTestId('fund-flow-sort-inflow').click()
      await expect(rows.first()).toContainText('证券')

      // 点击「流出」表头 → 切到 outflow desc
      // 行业流出额：证券7.5亿 > 银行4.2亿 > 半导体3亿 → desc 首行为证券
      await page.getByTestId('fund-flow-sort-outflow').click()
      await expect(rows.first()).toContainText('证券')
    })
  })

  test.describe('盘中变化视图（AC-05/AC-06）', () => {
    test('TC4 切换到变化视图，未选板块显示引导态', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 切换到盘中变化视图
      await page.getByTestId('fund-flow-view-chart').click()
      await expect(page.getByTestId('fund-flow-view-chart')).toHaveAttribute(
        'aria-selected',
        'true'
      )

      // AC-05：未选板块 → 引导态，不画空坐标系
      await expect(page.getByTestId('fund-flow-timeseries-guide')).toBeVisible()

      // 板块候选清单可见（来自行业维度排行榜：半导体/证券/银行）
      await expect(page.getByTestId('fund-flow-toggle-sector-半导体')).toBeVisible()
      await expect(page.getByTestId('fund-flow-toggle-sector-证券')).toBeVisible()
      await expect(page.getByTestId('fund-flow-toggle-sector-银行')).toBeVisible()
    })

    test('TC5 变化视图选板块叠加曲线，图表渲染', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 切换到盘中变化视图
      await page.getByTestId('fund-flow-view-chart').click()
      await expect(page.getByTestId('fund-flow-timeseries-guide')).toBeVisible()

      // 选择「半导体」+「证券」两个板块叠加（mock 按 sector_names 返回两条曲线）
      await page.getByTestId('fund-flow-toggle-sector-半导体').click()
      await page.getByTestId('fund-flow-toggle-sector-证券').click()

      // 已选板块 chip 区出现（AC-06：可移除）
      await expect(page.getByTestId('fund-flow-selected-sectors')).toBeVisible()
      await expect(page.getByTestId('fund-flow-remove-sector-半导体')).toBeVisible()
      await expect(page.getByTestId('fund-flow-remove-sector-证券')).toBeVisible()

      // 曲线图渲染（mock 返回 hasData=true，series 非空）
      await expect(page.getByTestId('fund-flow-timeseries-chart')).toBeVisible()

      // 移除一个板块 → 仅剩证券，图表仍渲染
      await page.getByTestId('fund-flow-remove-sector-半导体').click()
      await expect(page.getByTestId('fund-flow-remove-sector-半导体')).toHaveCount(0)
      await expect(page.getByTestId('fund-flow-remove-sector-证券')).toBeVisible()
      await expect(page.getByTestId('fund-flow-timeseries-chart')).toBeVisible()
    })
  })

  test.describe('加载失败错误态（AC-09）', () => {
    test('TC6 排行榜加载失败显示错误态与重试按钮', async ({ page }) => {
      // rankings 返回 500 → 错误态；timeseries/latest-date 仍正常（独立降级 AC-09）
      await mockFundFlowRankingsError(page)
      await mockFundFlowTimeseries(page)
      await mockFundFlowLatestDate(page, '2026-07-24')
      await page.goto(SECTOR_FUND_FLOW_PAGE)

      // 排行榜错误态可见 + 重试按钮
      await expect(page.getByTestId('fund-flow-ranking-error')).toBeVisible()
      await expect(page.getByTestId('fund-flow-ranking-retry')).toBeVisible()

      // 错误态下表格数据行不渲染
      await expect(
        page.locator('[data-testid="fund-flow-ranking-table"] tbody tr')
      ).toHaveCount(0)
    })
  })
})
