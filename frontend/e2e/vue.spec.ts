import { test, expect } from '@playwright/test'

// See here how to get started:
// https://playwright.dev/docs/intro
test('visits the app root url', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login$/)

  const submitButton = page.getByRole('button', { name: /Přihlásit/i })
  await expect(submitButton).toBeVisible()
  await expect(submitButton).toHaveAttribute('type', 'submit')
})
