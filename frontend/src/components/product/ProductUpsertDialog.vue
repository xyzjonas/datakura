<template>
  <q-dialog v-model="showDialog">
    <q-card class="w-full max-w-3xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-1" @submit="onSubmit">
          <q-input v-model.trim="form.name" outlined label="Název" :rules="[rules.notEmpty]" />
          <q-input v-model.trim="form.code" outlined label="Kód" :rules="[rules.notEmpty]" />

          <q-input v-model.trim="form.type" outlined label="Typ zboží" :rules="[rules.notEmpty]" />
          <q-input v-model.trim="form.group" outlined label="Skupina" hint="Volitelné" />

          <q-input v-model.trim="form.unit" outlined label="Jednotka" :rules="[rules.notEmpty]" />
          <q-input
            v-model.number="form.unit_weight"
            outlined
            type="number"
            min="0"
            step="0.01"
            label="Váha jednotky (g)"
          />

          <q-input
            v-model.number="form.purchase_price"
            outlined
            type="number"
            min="0"
            step="0.01"
            label="Nákupní cena"
          />
          <q-input
            v-model.number="form.base_price"
            outlined
            type="number"
            min="0"
            step="0.01"
            label="Prodejní cena"
          />

          <q-input v-model.trim="form.currency" outlined label="Měna" :rules="[rules.notEmpty]" />
          <q-input
            v-model.trim="form.customs_declaration_group"
            outlined
            label="Celní nomenklatura"
            hint="Volitelné"
          />

          <q-input
            v-model="attributesJson"
            class="md:col-span-2"
            type="textarea"
            autogrow
            outlined
            label="Atributy (JSON)"
            hint='Volitelné, například {"barva": "modrá"}'
          />

          <div class="md:col-span-2 mt-2 flex justify-end">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              :loading="loading"
              :label="submitLabel"
              class="h-[3rem] min-w-[10rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { ProductCreateOrUpdateSchema } from '@/client'
import { rules } from '@/utils/rules'
import { useQuasar } from 'quasar'
import { computed, ref, watch } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<ProductCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Produkt',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: ProductCreateOrUpdateSchema): void
}>()

const $q = useQuasar()

const attributesJson = ref('{}')

const normalizedAttributes = computed(() => {
  const value = attributesJson.value.trim()
  if (!value) {
    return {}
  }

  const parsed = JSON.parse(value)
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('Atributy musí být JSON objekt')
  }

  return Object.fromEntries(Object.entries(parsed).map(([key, val]) => [key, String(val)]))
})

const syncAttributesFromForm = () => {
  const attrs = form.value.attributes ?? {}
  attributesJson.value = Object.keys(attrs).length > 0 ? JSON.stringify(attrs, null, 2) : '{}'
}

watch(showDialog, (visible) => {
  if (visible) {
    syncAttributesFromForm()
  }
})

const onSubmit = () => {
  try {
    form.value.attributes = normalizedAttributes.value
  } catch {
    $q.notify({
      type: 'warning',
      message: 'Pole atributy obsahuje neplatný JSON objekt.',
    })
    return
  }

  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
