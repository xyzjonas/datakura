import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import '@/assets/styles.scss'
import { Quasar } from 'quasar'

// First reset
import '@unocss/reset/tailwind.css'
// Then Quasar styling
import 'quasar/src/css/index.sass'
// Then UnoCSS styling
import 'virtual:uno.css'

// Material icons are needed for some components default icons (arrows and such)
import '@quasar/extras/material-icons/material-icons.css'
import '@quasar/extras/material-symbols-outlined/material-symbols-outlined.css'

const app = createApp(App)

app.use(router)

app.use(Quasar, {
  plugins: {}, // import Quasar plugins and add here
})

app.mount('#app')
