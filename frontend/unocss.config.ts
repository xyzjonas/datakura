import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  rules: [],
  shortcuts: {
    link: 'text-current light:text-primary font-600 no-underline hover:underline',
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
      pine: '#0c322c', // Pine
      primary: '#2d5a52',
      green: '#30ba78', // Jungle
      'light-green': '#90ebcd', // Mint
      secondary: '#192072', // Midnight
      blue: '#2453ff', // Waterhole
      accent: '#fe7c3f', // Persimmon
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
