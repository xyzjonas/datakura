<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Změnit slevovou skupinu</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-select
            v-model="selectedCode"
            label="Slevová skupina"
            :options="options"
            emit-value
            map-options
            clearable
            outlined
          />

          <q-btn
            type="submit"
            unelevated
            color="primary"
            label="Uložit"
            class="h-[3rem] mt-3"
            :loading="loading"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { DiscountGroupSchema } from '@/client'
import { computed, ref, watch } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })

const props = defineProps<{
  loading?: boolean
  currentCode?: string | null
  groups: DiscountGroupSchema[]
}>()

const emit = defineEmits<{
  (e: 'submit', groupCode: string | null): void
}>()

const selectedCode = ref<string | null>(null)

watch(
  () => showDialog.value,
  (visible) => {
    if (visible) {
      selectedCode.value = props.currentCode ?? null
    }
  },
  { immediate: true },
)

const options = computed(() =>
  props.groups
    .filter((group) => group.is_active)
    .map((group) => ({
      label: `${group.name} (${group.discount_percent} %)`,
      value: group.code,
    })),
)

const onSubmit = () => {
  emit('submit', selectedCode.value ?? null)
}

const loading = computed(() => props.loading ?? false)
</script>
