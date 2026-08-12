import { test as base, expect } from '@playwright/test'
import {
  createTestShareholderGroups,
  createQFiiGroup,
  createSocialGroup,
  createSocialGroupWithEmptyAndZero,
  mockShareholderGroupsList,
  mockShareholderGroupsListError,
  mockShareholderGroupCreate,
  mockShareholderGroupCreateConflict,
  mockShareholderGroupUpdate,
  mockShareholderGroupDelete,
  mockShareholderGroupPreview,
  mockShareholderGroupPreviewBreakdown,
  mockShareholderGroupPreviewBreakdownError,
  mockShareholderGroupPreviewBreakdownSequence,
  mockShareholderGroupKeywordMatches,
  mockShareholderGroupKeywordMatchesError,
  mockShareholderGroupDetail,
} from './helpers/mock-shareholder-api'

const ADMIN_GROUPS_PAGE = '/dashboard/admin/shareholder-groups'

/**
 * 扩展 test fixture：在每个测试前注入管理员认证
 *
 * 参照 admin-fund-sync.spec.ts 模式：本项目使用自定义 JWT（token 存 localStorage），
 * 同时注入 Cookie access_token。role 设为 admin 以通过管理端路由守卫。
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
            id: 'test-admin-id',
            email: 'admin@test.com',
            username: 'TestAdmin',
            is_active: true,
            role: 'admin',
          })
        )
      })
      await use()
    },
    { auto: true },
  ],
})

test.describe('AC-06/07/10：股东分组管理面板（plan-03）', () => {
  test.describe('页面入口与列表展示', () => {
    test('TC-1.1 管理员侧边栏可见"股东分组管理"导航项，点击进入分组管理页', async ({
      page,
    }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])
      await page.route(
        (url) => url.pathname === '/api/v1/admin/tasks/stats/summary',
        (route) => route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            pending: 0,
            running: 0,
            completed: 0,
            failed: 0,
            cancelled: 0,
            total: 0,
          }),
        })
      )
      await page.route(
        (url) => url.pathname === '/api/v1/admin/tasks',
        (route) => route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ tasks: [], total: 0, page: 1 }),
        })
      )

      // 访问管理后台首页
      await page.goto('/dashboard/admin')

      // 断言：侧边栏含"股东分组管理"导航项
      const sidebar = page.locator('aside')
      await expect(sidebar.getByRole('link', { name: '股东分组管理' })).toBeVisible()

      // 点击导航项
      await sidebar.getByRole('link', { name: '股东分组管理' }).click()

      // 断言：URL 变为分组管理页
      await expect(page).toHaveURL(/\/dashboard\/admin\/shareholder-groups/)

      // 断言：main 区域含页面标题"股东分组管理"
      const main = page.locator('main')
      await expect(main.getByRole('heading', { name: '股东分组管理' })).toBeVisible()
    })

    test('TC-1.2 分组列表展示 5 个预定义组（名称/规则数/匹配股数）', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      const table = main.locator('table').first()

      // 断言：5 个预定义组名都可见 — 用精确匹配避免"私募基金"误匹配其他文案
      for (const g of groups) {
        await expect(table.getByText(g.name, { exact: true })).toBeVisible()
      }

      // 断言：表头含关键列
      await expect(table.getByText('匹配规则数', { exact: true }).first()).toBeVisible()
      await expect(table.getByText('匹配股数', { exact: true }).first()).toBeVisible()
      await expect(table.getByText('操作', { exact: true }).first()).toBeVisible()
    })

    test('TC-1.3 顶部"新增分组"按钮可见', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      await expect(
        main.getByRole('button', { name: /^新增分组/ })
      ).toBeVisible()
    })
  })

  test.describe('新增分组（AC-06）', () => {
    test('TC-1.4 新增 QFII 分组：组名 + 关键词保存后列表刷新出现新分组', async ({
      page,
    }) => {
      const initialGroups = createTestShareholderGroups()
      const afterGroups = [...initialGroups, createQFiiGroup()]
      await mockShareholderGroupsList(page, [initialGroups, afterGroups])
      await mockShareholderGroupCreate(page, createQFiiGroup())
      // 填关键词会触发 preview / preview-breakdown，mock 之避免实际请求
      await mockShareholderGroupPreview(page, 5)
      await mockShareholderGroupPreviewBreakdown(page, [
        { keyword: '瑞士银行', matchedStockCount: 5 },
        { keyword: '摩根大通', matchedStockCount: 3 },
      ])

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')

      // 点击"新增分组" → 跳转 /new
      await main.getByRole('button', { name: /^新增分组/ }).click()
      await expect(page).toHaveURL(/\/shareholder-groups\/new$/)

      // 填组名 QFII — 用 placeholder 或 label 定位组名 input
      const nameInput = page.getByLabel(/组名/).or(page.locator('input').first())
      await nameInput.fill('QFII')

      // 第一个关键词
      const keywordInputs = page.locator('input[type="text"]')
      await keywordInputs.nth(0).fill('瑞士银行')
      // 添加第二个关键词
      await page.getByRole('button', { name: /添加关键词/ }).click()
      await keywordInputs.nth(1).fill('摩根大通')

      // 保存 → 回列表
      await page.getByRole('button', { name: /^保存$/ }).click()
      await expect(page).toHaveURL(/\/dashboard\/admin\/shareholder-groups$/)

      // 断言：列表刷新可见"QFII"行
      const table = main.locator('table').first()
      await expect(table.getByText('QFII', { exact: true })).toBeVisible({ timeout: 10000 })
    })

    test('TC-1.6 关键词变化触发匹配预览', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])
      await mockShareholderGroupPreview(page, 3)
      await mockShareholderGroupPreviewBreakdown(page, [
        { keyword: '瑞士银行', matchedStockCount: 3 },
      ])

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      await main.getByRole('button', { name: /^新增分组/ }).click()
      await expect(page).toHaveURL(/\/shareholder-groups\/new$/)

      // 填组名
      const nameInput = page.getByLabel(/组名/).or(page.locator('input').first())
      await nameInput.fill('QFII')

      // 输入关键词 — 触发 debounce 预览
      const keywordInput = page.locator('input[type="text"]').first()
      await keywordInput.fill('瑞士银行')

      // 断言：预览区显示匹配股数
      await expect(
        page.getByText(/合并匹配\s*3\s*只|匹配到?\s*3\s*只股票|匹配\s*3\s*只/)
      ).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('编辑分组（AC-07）', () => {
    test('TC-1.5 编辑国家队分组：预填充关键词，保存后回列表', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])
      // 编辑页按 id 加载详情
      await mockShareholderGroupDetail(page, groups[0])
      await mockShareholderGroupUpdate(page)
      // 预填充关键词会触发 debounce 预览，mock 之避免实际请求
      await mockShareholderGroupPreview(page, 10)
      await mockShareholderGroupPreviewBreakdown(page, [
        { keyword: '中央汇金', matchedStockCount: 5 },
        { keyword: '中国证金', matchedStockCount: 4 },
        { keyword: '国家集成电路产业投资基金', matchedStockCount: 3 },
      ])

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      const table = main.locator('table').first()

      // 点击"国家队"行的"编辑"按钮
      const nationalRow = table.locator('tr').filter({ hasText: '国家队' })
      await nationalRow.getByRole('button', { name: /^编辑$/ }).click()

      // 跳转 /{id}
      await expect(page).toHaveURL(/\/shareholder-groups\/1$/)

      // 断言：关键词预填充"中央汇金"可见（aria-label = 关键词值）
      await expect(page.getByRole('textbox', { name: /中央汇金/ })).toBeVisible({
        timeout: 10000,
      })

      // 点击保存 → 回列表
      await page.getByRole('button', { name: /^保存$/ }).click()
      await expect(page).toHaveURL(/\/dashboard\/admin\/shareholder-groups$/)
    })
  })

  test.describe('删除分组（AC-10）', () => {
    // 测试 bug 修复说明：mock 数据中"外资投行"组描述为"合格境外机构投资者（QFII）"，
    // 与 QFII 组名共用子串"QFII"，导致 tr.filter({ hasText: 'QFII' }) 匹配 2 行（strict
    // mode violation）。改为先用精确文本 QFII 定位组名 span（外资投行行仅含 "（QFII）"
    // 子串，getByText({exact:true}) 不匹配），再向上找其所在 tr。
    const qfiiRowLocator = (table: import('@playwright/test').Locator) =>
      table.getByText('QFII', { exact: true }).locator('xpath=ancestor::tr')

    test('TC-1.7 点击删除弹出确认对话框含"取消"和"确认删除"', async ({ page }) => {
      const groups = [...createTestShareholderGroups(), createQFiiGroup()]
      await mockShareholderGroupsList(page, [groups])

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      const table = main.locator('table').first()

      // 点击"QFII"行的"删除"按钮
      const qfiiRow = qfiiRowLocator(table)
      await qfiiRow.getByRole('button', { name: /^删除$/ }).click()

      // 断言：弹出 AlertDialog
      // 测试兼容性说明：实现按 plan-03 §3.2 使用 shadcn AlertDialog（Radix 强制 role=alertdialog），
      // 故用 getByRole('alertdialog') 而非 'dialog' 定位删除确认框
      const dialog = page.getByRole('alertdialog')
      await expect(dialog).toBeVisible()

      // 断言：dialog 内含"QFII"组名
      await expect(dialog.getByText('QFII', { exact: true })).toBeVisible()

      // 断言：含"取消"和"确认删除"按钮
      await expect(dialog.getByRole('button', { name: /^取消$/ })).toBeVisible()
      await expect(dialog.getByRole('button', { name: /^确认删除$/ })).toBeVisible()
    })

    test('TC-1.8 确认删除：点击"确认删除"后 QFII 从列表消失', async ({ page }) => {
      const initialGroups = [...createTestShareholderGroups(), createQFiiGroup()]
      const afterGroups = createTestShareholderGroups() // 不含 QFII
      await mockShareholderGroupsList(page, [initialGroups, afterGroups])
      await mockShareholderGroupDelete(page)

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      const table = main.locator('table').first()

      // 触发删除确认
      const qfiiRow = qfiiRowLocator(table)
      await qfiiRow.getByRole('button', { name: /^删除$/ }).click()

      const dialog = page.getByRole('alertdialog')
      await dialog.getByRole('button', { name: /^确认删除$/ }).click()

      // 断言：dialog 关闭
      await expect(dialog).toBeHidden({ timeout: 10000 })

      // 断言：列表刷新后不再出现"QFII"行（限定 main 区域 table）
      await expect(table.getByText('QFII', { exact: true })).toBeHidden({ timeout: 10000 })
    })

    test('TC-1.9 取消删除：点击"取消"不执行删除，列表保留 QFII', async ({ page }) => {
      const groups = [...createTestShareholderGroups(), createQFiiGroup()]
      await mockShareholderGroupsList(page, [groups])
      await mockShareholderGroupDelete(page) // 不应被调用

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      const table = main.locator('table').first()

      // 触发删除确认
      const qfiiRow = qfiiRowLocator(table)
      await qfiiRow.getByRole('button', { name: /^删除$/ }).click()

      const dialog = page.getByRole('alertdialog')
      await dialog.getByRole('button', { name: /^取消$/ }).click()

      // 断言：dialog 关闭
      await expect(dialog).toBeHidden({ timeout: 10000 })

      // 断言：列表仍含 QFII 行
      await expect(table.getByText('QFII', { exact: true })).toBeVisible()
    })
  })

  test.describe('错误与边界', () => {
    test('TC-1.10 新增组名重复时提示错误', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])
      await mockShareholderGroupCreateConflict(page)

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      await main.getByRole('button', { name: /^新增分组/ }).click()
      await expect(page).toHaveURL(/\/shareholder-groups\/new$/)

      // 填已存在的组名"国家队"
      const nameInput = page.getByLabel(/组名/).or(page.locator('input').first())
      await nameInput.fill('国家队')

      await page.getByRole('button', { name: /^保存$/ }).click()

      // 断言：编辑页内 inline 错误提示可见
      await expect(page.getByText('组名已存在', { exact: true })).toBeVisible({ timeout: 10000 })
    })

    test('TC-1.11 列表 API 返回 500 时展示加载失败提示', async ({ page }) => {
      await mockShareholderGroupsListError(page)

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      // 断言：可见加载失败/错误提示（兼容多种文案）
      await expect(
        main.getByText(/加载失败|加载出错|请求失败|失败/)
      ).toBeVisible({ timeout: 10000 })
    })
  })
})

// ============================================================================
// plan-02：编辑页逐关键词股数与明细下钻（AC-01 ~ AC-09）
//
// 来源：docs/07-股东分组匹配明细/07-2-实现计划-股东分组匹配明细/plan-02-...md
// 用例文档：docs/e2e/07-e2e-用例-股东分组匹配明细.md
//
// 重构后（弹窗 → 整页）：编辑从 dialog 改为路由页 /{id}，data-testid 断言不变。
// ============================================================================

test.describe('plan-02：编辑页逐关键词股数与明细下钻（AC-01 ~ AC-09）', () => {
  test('TC-2.1 编辑页显示逐关键词股数 + 合并预览（AC-01, AC-02）', async ({ page }) => {
    const group = createSocialGroup()
    await mockShareholderGroupsList(page, [[group]])
    await mockShareholderGroupDetail(page, group)
    // LIFO：先注册前缀 preview，再注册精确 preview-breakdown，让精确先命中
    await mockShareholderGroupPreview(page, 3) // 合并去重
    await mockShareholderGroupPreviewBreakdown(page, [
      { keyword: '全国社保', matchedStockCount: 2 },
      { keyword: '社保基金', matchedStockCount: 3 },
    ])

    await page.goto(ADMIN_GROUPS_PAGE)
    await page.getByRole('button', { name: /^编辑$/ }).first().click()
    await expect(page).toHaveURL(/\/shareholder-groups\/1$/)

    // AC-01：每个非空关键词行显示「X 只」标签
    await expect(page.locator('[data-testid="keyword-count-0"]')).toContainText('2 只')
    await expect(page.locator('[data-testid="keyword-count-1"]')).toContainText('3 只')

    // AC-02：底部合并预览仍在（与逐关键词股数并存）
    await expect(page.getByText(/合并匹配\s*\d+\s*只|匹配\s*3\s*只/)).toBeVisible()
  })

  test('TC-2.2 点击查看明细展开三列，多股东分行按股票代码升序（AC-03, AC-04, AC-05）', async ({ page }) => {
    const group = createSocialGroup()
    await mockShareholderGroupsList(page, [[group]])
    await mockShareholderGroupDetail(page, group)
    await mockShareholderGroupPreview(page, 3)
    await mockShareholderGroupPreviewBreakdown(page, [
      { keyword: '全国社保', matchedStockCount: 3 },
      { keyword: '社保基金', matchedStockCount: 3 },
    ])
    // mock 数据：600000 两个不同 holder + 600036 一个 holder（验证多股东分行 + 升序）
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
    await expect(page).toHaveURL(/\/shareholder-groups\/1$/)

    // 点击第一个关键词的「查看明细」按钮（用 data-testid 避免多元素匹配，规则 5）
    await page.locator('[data-testid="view-detail-0"]').click()

    // AC-03：三列表头可见
    await expect(page.getByRole('columnheader', { name: '股票代码' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: '股票名称' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: '股东名称' })).toBeVisible()

    // AC-04：600000 出现 2 行（不同 holderName）
    const rows = page.locator('[data-testid="keyword-detail-panel"] tbody tr')
    await expect(rows).toHaveCount(3)
    await expect(rows.nth(0).locator('td').nth(0)).toHaveText('600000')
    await expect(rows.nth(1).locator('td').nth(0)).toHaveText('600000')
    // 行 0 / 行 1 的 holderName 不同（多股东分行）
    const holder0 = await rows.nth(0).locator('td').nth(2).textContent()
    const holder1 = await rows.nth(1).locator('td').nth(2).textContent()
    expect(holder0).not.toBeNull()
    expect(holder0).not.toEqual(holder1)

    // AC-05：按 symbol 升序
    const symbols = await rows.locator('td').nth(0).allTextContents()
    const sorted = [...symbols].sort()
    expect(symbols).toEqual(sorted)
  })

  test('TC-2.3 修改关键词后股数与已展开明细实时刷新（AC-06）', async ({ page }) => {
    const group = createSocialGroup()
    await mockShareholderGroupsList(page, [[group]])
    await mockShareholderGroupDetail(page, group)
    // preview 合并预览 mock（避免 401 触发 handleUnauthorizedRedirect 中断测试）
    await mockShareholderGroupPreview(page, 2)

    // preview-breakdown：第一次（初始加载）返回 2 只；第二次（修改后）返回 5 只
    await mockShareholderGroupPreviewBreakdownSequence(page, [
      [{ keyword: '全国社保', matchedStockCount: 2 }],
      [{ keyword: '全国社保基金', matchedStockCount: 5 }],
    ])
    // keyword-matches：固定返回 1 条（验证刷新后能重新加载）
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
    await expect(page).toHaveURL(/\/shareholder-groups\/1$/)

    // 初始：第一个关键词显示 2 只
    await expect(page.locator('[data-testid="keyword-count-0"]')).toContainText('2 只', {
      timeout: 10000,
    })

    // 展开明细
    await page.locator('[data-testid="view-detail-0"]').click()
    await expect(page.locator('[data-testid="keyword-detail-panel"]')).toBeVisible()

    // 修改第一个关键词 → 触发 500ms debounce → preview-breakdown 重新调用
    await page.locator('input[type="text"]').first().fill('全国社保基金')

    // 等待 debounce（500ms）+ buffer（100ms）
    await page.waitForTimeout(600)

    // AC-06：股数从 2 只刷新到 5 只
    await expect(page.locator('[data-testid="keyword-count-0"]')).toContainText('5 只', {
      timeout: 10000,
    })
  })

  test('TC-2.4 后端 500 时股数和明细显示重试按钮且保存可用（AC-07）', async ({ page }) => {
    const group = createSocialGroup()
    await mockShareholderGroupsList(page, [[group]])
    await mockShareholderGroupDetail(page, group)
    // preview 合并预览 mock（避免 401 触发 handleUnauthorizedRedirect 中断测试）
    await mockShareholderGroupPreview(page, 2)
    // preview-breakdown 整体失败（500）→ 股数区显示错误
    await mockShareholderGroupPreviewBreakdownError(page, 500)
    // keyword-matches 失败（500）→ 明细区显示错误
    await mockShareholderGroupKeywordMatchesError(page, 500)
    // 编辑保存 mock（沿用现有 helper）
    await mockShareholderGroupUpdate(page, group)

    await page.goto(ADMIN_GROUPS_PAGE)
    await page.getByRole('button', { name: /^编辑$/ }).first().click()
    await expect(page).toHaveURL(/\/shareholder-groups\/1$/)

    // AC-07：股数区显示「加载失败」
    await expect(page.getByText(/加载失败/).first()).toBeVisible({ timeout: 10000 })

    // 点击查看明细 → 明细区显示「加载失败」
    await page.locator('[data-testid="view-detail-0"]').click()
    await expect(
      page.locator('[data-testid="keyword-detail-panel"]').getByText(/加载失败/)
    ).toBeVisible({ timeout: 10000 })

    // 保存按钮始终可点击
    const saveButton = page.getByRole('button', { name: /^保存$/ })
    await expect(saveButton).toBeEnabled()

    // 点击保存成功 → 回列表
    await saveButton.click()
    await expect(page).toHaveURL(/\/dashboard\/admin\/shareholder-groups$/)
  })

  test('TC-2.5 空关键词不显示股数和按钮，0 匹配按钮置灰（AC-08, AC-09）', async ({ page }) => {
    // 用专用工厂：含空关键词 + 0 匹配关键词
    const group = createSocialGroupWithEmptyAndZero()
    await mockShareholderGroupsList(page, [[group]])
    await mockShareholderGroupDetail(page, group)
    // preview 合并预览 mock（避免 401 触发 handleUnauthorizedRedirect 中断测试）
    await mockShareholderGroupPreview(page, 2)
    await mockShareholderGroupPreviewBreakdown(page, [
      { keyword: '全国社保', matchedStockCount: 2 },
      { keyword: '无匹配关键词', matchedStockCount: 0 },
    ])

    await page.goto(ADMIN_GROUPS_PAGE)
    await page.getByRole('button', { name: /^编辑$/ }).first().click()
    await expect(page).toHaveURL(/\/shareholder-groups\/1$/)

    // AC-08：空关键词行（index 1）无 count 标签 + 无查看明细按钮
    await expect(page.locator('[data-testid="keyword-count-1"]')).toHaveCount(0)
    await expect(page.locator('[data-testid="view-detail-1"]')).toHaveCount(0)

    // AC-09：0 匹配关键词（index 2）的按钮 disabled
    await expect(page.locator('[data-testid="view-detail-2"]')).toBeDisabled()
    // 非 0 关键词（index 0）按钮 enabled
    await expect(page.locator('[data-testid="view-detail-0"]')).toBeEnabled()
  })
})
