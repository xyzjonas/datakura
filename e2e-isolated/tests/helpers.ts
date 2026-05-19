import { expect, Page } from "@playwright/test";

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const credentials = {
  username: requiredEnv("E2E_USERNAME"),
  password: requiredEnv("E2E_PASSWORD"),
};

export async function dismissReleaseDialogIfPresent(page: Page): Promise<void> {
  const readButton = page.getByRole("button", { name: /přečteno/i }).first();
  if (await readButton.isVisible().catch(() => false)) {
    await readButton.click();
    return;
  }

  const dontBotherButton = page
    .getByRole("button", { name: /teď neotravuj/i })
    .first();
  if (await dontBotherButton.isVisible().catch(() => false)) {
    await dontBotherButton.click();
  }
}

export async function login(page: Page): Promise<void> {
  await page.goto("/login");

  await page
    .getByRole("textbox", { name: /e-mail/i })
    .fill(credentials.username);
  await page
    .getByRole("textbox", { name: /heslo/i })
    .fill(credentials.password);
  await page.getByRole("button", { name: /přihlásit/i }).click();

  await expect(page).toHaveURL(/^(?!.*\/login).*$/);
  await dismissReleaseDialogIfPresent(page);
  await expect(page.getByText(credentials.username).first()).toBeVisible();
}

export async function logout(page: Page): Promise<void> {
  await page
    .getByRole("button")
    .filter({ hasText: /more_vert/i })
    .first()
    .click();
  await page
    .getByText(/odhlásit/i)
    .first()
    .click();

  await expect(page).toHaveURL(/\/login/);
  await expect(
    page.getByRole("heading", { name: /přihlášení/i }),
  ).toBeVisible();
}

export async function createOrderAndCancel(page: Page): Promise<string> {
  await page.goto("/orders?tab=outbound");
  await dismissReleaseDialogIfPresent(page);

  await page
    .getByRole("button", { name: /^vytvořit$/i })
    .first()
    .click();

  const createDialog = page
    .getByRole("dialog")
    .filter({ hasText: /nová objednávka/i });
  await expect(createDialog).toBeVisible();

  const customerInput = createDialog.getByRole("combobox", {
    name: /vyhledat zákazníka/i,
  });
  await customerInput.fill("Jan");
  await customerInput.press("Enter");
  await page.getByRole("option", { name: /jan novák/i }).click();

  const externalCode = `BOT-E2E-${Date.now()}`;
  await createDialog
    .getByRole("textbox", { name: /externí číslo/i })
    .fill(externalCode);
  await createDialog.getByRole("button", { name: /^vytvořit$/i }).click();

  await expect(page).toHaveURL(/\/outbound-orders\//);
  await expect(page.getByText(externalCode).first()).toBeVisible();

  await page.getByRole("button", { name: /uzavřít/i }).click();

  const closeDialog = page
    .getByRole("dialog")
    .filter({ hasText: /uzavřít přijatou objednávku/i });
  await expect(closeDialog).toBeVisible();
  await closeDialog.getByRole("button", { name: /^potvrdit$/i }).click();

  await expect(page.getByText(/zrušeno/i).first()).toBeVisible();
  return externalCode;
}
