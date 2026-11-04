import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

// The source SVG is a full-bleed square with the glyph inside the maskable safe zone,
// so no extra padding / white backdrop is needed for the maskable and apple icons.
export default defineConfig({
  preset: {
    ...minimal2023Preset,
    transparent: { ...minimal2023Preset.transparent, padding: 0 },
    maskable: { sizes: [512], padding: 0 },
    apple: { sizes: [180], padding: 0 },
  },
  images: ['public/logo.svg'],
})
