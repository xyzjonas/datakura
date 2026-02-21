import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  rules: [],
  shortcuts: {
    link: 'text-current text-primary font-600 no-underline hover:underline hover:cursor-pointer',
    description: 'light:bg-gray-2 dark:bg-gray-6 p-4 rounded-lg my-1 shadow shadow-inset',
  },
  presets: [
    // Tailwind-like utility classes, replacement for Bootstrap's utility classes.
    presetUno({
      // Align tailwind darkmode to Quasar's classes,
      // so that darkmode selectors (e.g. 'dark:color-red') can be used as well.
      dark: {
        light: '.body--light',
        dark: '.body--dark',
      },
    }),
  ],
  // duplicated for Quasar in quasar-variables.scss
  // https://brand.suse.com/brand-system/color-palette
  theme: {
    colors: {
      // primary: '#cc3263',
      primary: '#1976d2',
      primary_light: '#1976d27b',
      secondary: '#192072', // Midnight
      accent: '#3f84e5', // blue
      red: '#d92b2b',
      'light-red': '#fee2e2',
      white: '#ffffff',
      grey: '#efefef', // Fog
      'grey-1': '#fafafa',
      'grey-2': '#f1f1f1', // Cloud
      'grey-8': '#6d6d6d',
      'shadow-color': '#666',
      'dark-shadow-color': '#444',
      'dark-3': '#424242',
      'dark-5': '#3a3a3a',
    },
    fontSize: {
      '2xs': '0.625rem', // 10px
    },
  },
})
