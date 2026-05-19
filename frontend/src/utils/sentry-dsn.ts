export function getSentryDsn() {
  return document.querySelector('meta[name="sentry-dsn"]')?.getAttribute('content') ?? undefined
}

export function getSentryEnvironment() {
  return (
    document.querySelector('meta[name="sentry-environment"]')?.getAttribute('content') ?? undefined
  )
}
