import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import '@/assets/styles.scss'
import { Notify, Loading, Quasar } from 'quasar'

// First reset
import '@unocss/reset/tailwind.css'
// Then Quasar styling
import 'quasar/src/css/index.sass'
// Then UnoCSS styling
import 'virtual:uno.css'

// Material icons are needed for some components default icons (arrows and such)
import '@quasar/extras/material-icons/material-icons.css'
import '@quasar/extras/material-symbols-outlined/material-symbols-outlined.css'

import * as Sentry from '@sentry/vue'
import { getSentryDsn, getSentryEnvironment } from './utils/sentry-dsn'

const app = createApp(App)

const sentryDsn = getSentryDsn()
const sentryEnvironment = getSentryEnvironment() ?? 'development'
if (!sentryDsn) {
  console.warn('Sentry DSN not found, Sentry will not be initialized')
} else {
  console.info(`Initializing Sentry (env=${sentryEnvironment}) with DSN:`, sentryDsn)
  Sentry.init({
    app,
    dsn: sentryDsn,
    // Setting this option to true will send default PII data to Sentry.
    // For example, automatic IP address collection on events
    sendDefaultPii: false,
    environment: sentryEnvironment,
  })
}

app.use(router)

app.use(Quasar, {
  plugins: { Notify, Loading },
})

Notify.setDefaults({
  progress: true,
  position: 'top-right',
  classes: 'w-full',
})

app.directive('decimal', {
  mounted(el, binding) {
    el.textContent = Number(binding.value).toFixed(2)
  },
  updated(el, binding) {
    el.textContent = Number(binding.value).toFixed(2)
  },
})

app.mount('#app')
