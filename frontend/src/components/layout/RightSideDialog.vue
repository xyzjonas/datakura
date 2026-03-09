<template>
  <q-dialog v-model="showDialog" position="right" full-height>
    <q-card class="h-screen max-h-screen flex flex-col" :class="panelClass">
      <div class="p-4 flex items-center gap-2 border-b border-gray-3">
        <slot name="header">
          <span class="text-xl">{{ title }}</span>
        </slot>
        <q-space />
        <q-btn flat round icon="close" @click="showDialog = false" />
      </div>

      <div class="flex-1 overflow-auto p-4">
        <slot />
      </div>

      <!-- <div v-if="$slots.footer" class="p-4 border-t border-gray-3">
        <slot name="footer" />
      </div> -->
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
type Props = {
  title?: string
  panelClass?: string
}

withDefaults(defineProps<Props>(), {
  title: '',
  panelClass: 'w-[min(100vw,720px)]',
})

const showDialog = defineModel<boolean>('show', { default: false })
</script>
