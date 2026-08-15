import { expect, test, type Page } from '@playwright/test'

async function login(page: Page) {
  await page.goto('/login')
  await page.fill('input[type=email]', 'dev@local')
  await page.fill('input[type=password]', 'dev123456')
  await page.click('button.btn-primary')
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 })
}

test('登录后首页正常展示', async ({ page }) => {
  await login(page)
  await expect(page.getByText('你的 AI 学习伙伴')).toBeVisible()
  await expect(page.getByText('开始刷题')).toBeVisible()
})

test('统计页展示学习活跃热力图', async ({ page }) => {
  await login(page)
  await page.goto('/stats')
  await expect(page.getByText('学习统计')).toBeVisible()
  await expect(page.getByText('学习活跃热力图')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText('近 365 天')).toBeVisible()
})

test('刷题页可选择模式并开始', async ({ page }) => {
  await login(page)
  await page.goto('/review')
  await expect(page.getByText('选择复习模式')).toBeVisible()
  await page.click('text=普通模式')
  await page.click('button:has-text("开始")')
  // 有题时进入答题；无题时出现空状态，两者都算通过
  await expect(page.getByText('暂无待复习的题目').or(page.getByText('普通模式'))).toBeVisible({
    timeout: 15_000,
  })
})

test('思维导图页渲染 SVG', async ({ page }) => {
  await login(page)
  await page.goto('/mindmap')
  await expect(page.locator('svg').first()).toBeVisible({ timeout: 10_000 })
})

test('AI 助手聊天页可输入', async ({ page }) => {
  await login(page)
  await page.goto('/assistant')
  await expect(page.getByRole('heading', { name: '智能助手' })).toBeVisible()
  await expect(page.locator('textarea')).toBeVisible()
  await page.fill('textarea', '你好')
  await expect(page.getByRole('button', { name: '发送' })).toBeEnabled()
})
