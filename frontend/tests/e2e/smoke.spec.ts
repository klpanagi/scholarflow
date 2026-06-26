import { test, expect } from "@playwright/test"

/**
 * Smoke tests - verify all routes render correctly
 * Run with: pnpm playwright test --grep "@smoke"
 */

const PUBLIC_ROUTES = ["/", "/login", "/register"] as const
const APP_SHELL_ROUTES = [
  "/dashboard",
  "/assets",
  "/cult/agents",
  "/cult/skills",
  "/cult/chat",
  "/workflows",
  "/settings",
] as const

test.describe("@smoke Route rendering", () => {
  for (const route of [...PUBLIC_ROUTES, ...APP_SHELL_ROUTES]) {
    test(`@smoke serves ${route}`, async ({ page }) => {
      const response = await page.goto(route, { waitUntil: "domcontentloaded" })
      expect(response, `no response for ${route}`).not.toBeNull()
      expect(response!.status(), `${route} status`).toBeLessThan(500)
    })
  }
})

test.describe("@smoke Theme toggle", () => {
  test("theme persists across reload", async ({ page }) => {
    await page.goto("/")
    const toggle = page.getByRole("button", { name: /toggle theme/i })
    if ((await toggle.count()) > 0) {
      const initial = await page.evaluate(() =>
        document.documentElement.classList.contains("dark")
      )
      await toggle.first().click()
      await page.waitForTimeout(200)
      const after = await page.evaluate(() =>
        document.documentElement.classList.contains("dark")
      )
      expect(after).not.toBe(initial)
      await page.reload()
      const persisted = await page.evaluate(() =>
        document.documentElement.classList.contains("dark")
      )
      expect(persisted).toBe(after)
    }
  })
})

test.describe("@smoke Sidebar navigation", () => {
  test("desktop sidebar visible at 1280px", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto("/dashboard")
    const sidebar = page.getByText("ScholarFlow", { exact: false }).first()
    await expect(sidebar).toBeVisible()
  })

  test("hamburger menu opens drawer on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto("/dashboard")
    const hamburger = page.getByRole("button", {
      name: /menu|open sidebar|toggle navigation/i,
    })
    if ((await hamburger.count()) > 0) {
      await hamburger.first().click()
      await page.waitForTimeout(300)
      const drawer = page.locator('[role="dialog"]')
      await expect(drawer).toBeVisible()
    }
  })
})
