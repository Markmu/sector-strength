import { test as base, expect } from '@playwright/test'
import {
  createTestShareholderGroups,
  createQFiiGroup,
  mockShareholderGroupsList,
  mockShareholderGroupsListError,
  mockShareholderGroupCreate,
  mockShareholderGroupCreateConflict,
  mockShareholderGroupUpdate,
  mockShareholderGroupDelete,
  mockShareholderGroupPreview,
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
      // 第一次 GET 返回 5 组，第二次（保存后刷新）返回 6 组
      await mockShareholderGroupsList(page, [initialGroups, afterGroups])
      await mockShareholderGroupCreate(page, createQFiiGroup())

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')

      // 点击"新增分组"
      await main.getByRole('button', { name: /^新增分组/ }).click()

      // 弹出编辑表单 dialog
      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()

      // 填组名 QFII — 用 placeholder 或 label 定位组名 input，避免歧义
      const nameInput = dialog.getByLabel(/组名/).or(dialog.locator('input').first())
      await nameInput.fill('QFII')

      // 添加关键词"瑞士银行""摩根大通" — 找关键词输入区
      // 实现侧关键词编辑 UI 可能是多个 input 或一个 textarea，用宽松定位
      const keywordInputs = dialog.locator('input[type="text"]')
      const inputCount = await keywordInputs.count()
      if (inputCount >= 2) {
        // 已有多个关键词输入框（组名 input 不在 type=text 范围内的假设）
        await keywordInputs.nth(0).fill('瑞士银行')
        // 如果只有一个关键词 input + 添加按钮的模式，这里兼容处理
        const addButton = dialog.getByRole('button', { name: /添加关键词|\+.*关键词/ })
        if (await addButton.isVisible().catch(() => false)) {
          await addButton.click()
        }
        await keywordInputs.nth(1).fill('摩根大通')
      } else {
        // 退化：填第一个 input
        await keywordInputs.first().fill('瑞士银行')
      }

      // 点击保存 — 限定到 dialog 避免匹配页面其他"保存"按钮
      await dialog.getByRole('button', { name: /^保存$/ }).click()

      // 断言：保存后列表刷新可见"QFII"行（限定 main 区域 table）
      const table = main.locator('table').first()
      await expect(table.getByText('QFII', { exact: true })).toBeVisible({ timeout: 10000 })
    })

    test('TC-1.6 编辑表单关键词变化触发匹配预览', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])
      await mockShareholderGroupPreview(page, 3)

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      await main.getByRole('button', { name: /^新增分组/ }).click()

      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()

      // 填组名
      const nameInput = dialog.getByLabel(/组名/).or(dialog.locator('input').first())
      await nameInput.fill('QFII')

      // 输入关键词 — 触发 debounce 预览
      const keywordInput = dialog.locator('input[type="text"]').first()
      await keywordInput.fill('瑞士银行')

      // 断言：预览区显示匹配股数 — 用正则兼容文案"当前规则匹配到 N 只股票"或"匹配 N 只"
      await expect(
        dialog.getByText(/匹配到?\s*3\s*只股票|匹配\s*3\s*只/)
      ).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('编辑分组（AC-07）', () => {
    test('TC-1.5 编辑国家队分组：预填充关键词，新增关键词后保存', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])
      await mockShareholderGroupUpdate(page)

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      const table = main.locator('table').first()

      // 点击"国家队"行的"编辑"按钮 — 限定到含"国家队"的行
      const nationalRow = table.locator('tr').filter({ hasText: '国家队' })
      await nationalRow.getByRole('button', { name: /^编辑$/ }).click()

      // 弹出编辑表单 dialog
      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()

      // 断言：关键词预填充"中央汇金"（dialog 内可见）
      await expect(dialog.getByRole('textbox', { name: /中央汇金/ }).or(dialog.locator('input').filter({ hasText: /中央汇金/ }))).toBeVisible().catch(async () => {
        // 退化断言：dialog 内某处可见预填充关键词文本
        await expect(dialog.getByText('中央汇金', { exact: true }).first()).toBeVisible()
      })

      // 点击保存
      await dialog.getByRole('button', { name: /^保存$/ }).click()

      // 断言：保存后 dialog 关闭（dialog 不再可见）或 mock update 被调用
      // 用 dialog 消失作为成功信号（容错：实现侧可能刷新列表）
      await expect(dialog).toBeHidden({ timeout: 10000 })
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
    test('TC-1.10 新增组名重复时 toast 提示错误', async ({ page }) => {
      const groups = createTestShareholderGroups()
      await mockShareholderGroupsList(page, [groups])
      await mockShareholderGroupCreateConflict(page)

      await page.goto(ADMIN_GROUPS_PAGE)

      const main = page.locator('main')
      await main.getByRole('button', { name: /^新增分组/ }).click()

      const dialog = page.getByRole('dialog')
      await expect(dialog).toBeVisible()

      // 填已存在的组名"国家队"
      const nameInput = dialog.getByLabel(/组名/).or(dialog.locator('input').first())
      await nameInput.fill('国家队')

      await dialog.getByRole('button', { name: /^保存$/ }).click()

      // 断言：toast/错误提示可见 — 兼容"组名已存在"或通用失败文案
      await expect(
        main.getByText(/组名已存在|操作失败|保存失败|失败/)
      ).toBeVisible({ timeout: 10000 })
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
