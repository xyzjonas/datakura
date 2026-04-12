<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-input
            v-model="localForm.name"
            label="Název"
            outlined
            :rules="[(v) => !!v || 'Povinné']"
          />
          <q-input
            v-model.number="localForm.discount_percent"
            label="Sleva (%)"
            outlined
            type="number"
            min="0"
            max="100"
            step="0.01"
            :rules="[rules.isPercentage]"
          />
          <q-toggle v-model="localForm.is_active" label="Aktivní" />

          <q-btn
            type="submit"
            unelevated
            color="primary"
            :label="submitLabel"
            class="h-[3rem] mt-3"
            :loading="loading"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { DiscountGroupCreateOrUpdateSchema } from '@/client'
import { rules } from '@/utils/rules'
import { computed, ref, watch } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<DiscountGroupCreateOrUpdateSchema>({ required: true })

const props = defineProps<{
  title: string
  submitLabel: string
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', body: DiscountGroupCreateOrUpdateSchema): void
}>()

const localForm = ref<DiscountGroupCreateOrUpdateSchema>({
  name: '',
  discount_percent: 0,
  is_active: true,
})

watch(
  () => form.value,
  (value) => {
    localForm.value = {
      name: value.name,
      discount_percent: value.discount_percent,
      is_active: value.is_active ?? true,
    }
  },
  { immediate: true, deep: true },
)

const onSubmit = () => {
  emit('submit', {
    name: localForm.value.name.trim(),
    discount_percent: Number(localForm.value.discount_percent),
    is_active: localForm.value.is_active ?? true,
  })
}

const loading = computed(() => props.loading ?? false)
</script>
