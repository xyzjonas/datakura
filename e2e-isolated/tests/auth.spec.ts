import { test } from "@playwright/test";

import { login, logout } from "./helpers";

test("login and logout", async ({ page }) => {
  await login(page);
  await logout(page);
});
