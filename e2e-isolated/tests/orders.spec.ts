import { expect, test } from "@playwright/test";

import { createOrderAndCancel, login, logout } from "./helpers";

test("create new order and cancel immediately", async ({ page }) => {
  await login(page);
  const externalCode = await createOrderAndCancel(page);

  await page.goto("/orders?tab=outbound");
  await expect(page.getByText(externalCode).first()).toHaveCount(0);

  await logout(page);
});
