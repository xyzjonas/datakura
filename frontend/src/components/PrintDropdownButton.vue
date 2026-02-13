<template>
  <q-btn-dropdown
    unelevated
    outline
    color="primary"
    label="PDF"
    icon="sym_o_picture_as_pdf"
    :loading="loading"
  >
    <q-list>
      <q-item
        v-for="item in items"
        :key="item.label"
        clickable
        v-close-popup
        @click="() => clickPrint(item)"
      >
        <q-item-section>
          <q-item-label>{{ item.label }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-icon name="sym_o_file_save" />
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface DropdownItem {
  label: string
  onClick: () => Promise<void>
}

defineProps<{
  items: DropdownItem[]
}>()

const loading = ref(false)
const clickPrint = async (item: DropdownItem) => {
  loading.value = true
  try {
    await item.onClick()
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped></style>
