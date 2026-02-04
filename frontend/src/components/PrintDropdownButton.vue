<template>
  <q-btn-dropdown unelevated outline color="primary" label="PDF" icon="sym_o_picture_as_pdf">
    <q-list>
      <q-item
        v-for="item in items"
        :key="item.label"
        clickable
        v-close-popup
        @click="() => item.onClick()"
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
interface DropdownItem {
  label: string
  onClick: () => void
}

defineProps<{
  items: DropdownItem[]
}>()
</script>

<style lang="scss" scoped></style>
