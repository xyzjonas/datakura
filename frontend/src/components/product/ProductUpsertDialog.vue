<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-3xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-input
            v-model.trim="form.name"
            outlined
            label="Název"
            hint="Interní název produktu"
            :rules="[rules.notEmpty]"
          />
          <q-input
            v-model.trim="form.code"
            outlined
            label="Kód"
            hint="Jedinečný identifikátor produktu"
            :rules="[rules.notEmpty]"
          />

          <ProductTypeSelect v-model="form.type" />
          <ProductGroupSelect v-model="form.group" />

          <UnitOfMeasureSelect v-model="form.unit" />
          <q-input
            v-model.number="form.unit_weight"
            outlined
            type="number"
            min="0"
            step="0.01"
            label="Váha jednotky (g)"
            hint="Hmotnost jedné jednotky v gramech"
            :rules="[rules.notEmpty, rules.atLeastZero]"
          />

          <q-input
            v-model.number="form.purchase_price"
            outlined
            type="number"
            min="0"
            step="0.01"
            label="Nákupní cena"
            hint="Cena, za kterou produkt nakupujete (automaticky přepočítáváno )"
          />
          <q-input
            v-model.number="form.base_price"
            outlined
            type="number"
            min="0"
            step="0.01"
            label="Prodejní cena"
            hint="Základní cena pro prodej"
          />

          <q-input
            v-model.trim="form.currency"
            outlined
            label="Měna"
            hint="Měna použitá pro nákupní a prodejní cenu"
            :rules="[rules.notEmpty]"
            readonly
          />
          <q-input
            v-model.trim="form.customs_declaration_group"
            outlined
            label="Celní nomenklatura"
            hint="Kód celní nomenklatury pro tento produkt (např. pro exportní dokumentaci)"
          />

          <div class="mt-ě">
            <div class="mb-1 flex items-center justify-between">
              <span class="text-sm text-gray-7">Atributy</span>
              <q-btn flat dense round icon="add" @click="addAttributeRow">
                <q-tooltip>Přidat atribut</q-tooltip>
              </q-btn>
            </div>

            <q-list bordered separator class="rounded">
              <q-item v-for="(row, index) in attributeRows" :key="index" class="px-2">
                <div class="w-full flex items-center justify-between gap-2">
                  <q-input v-model.trim="row.key" dense outlined class="flex-1" label="Atribut" />
                  <q-input v-model.trim="row.value" dense outlined class="flex-1" label="Hodnota" />
                  <q-btn
                    flat
                    dense
                    round
                    color="negative"
                    icon="delete"
                    @click="removeAttributeRow(index)"
                  />
                </div>
              </q-item>

              <q-item v-if="!attributeRows.length">
                <q-item-section class="text-gray-5">Žádné atributy</q-item-section>
              </q-item>
            </q-list>
          </div>

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
import ProductGroupSelect from '@/components/selects/ProductGroupSelect.vue'
import ProductTypeSelect from '@/components/selects/ProductTypeSelect.vue'
import UnitOfMeasureSelect from '@/components/selects/UnitOfMeasureSelect.vue'
import { rules } from '@/utils/rules'
import { ref, watch } from 'vue'

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

type AttributeRow = {
  key: string
  value: string
}

const attributeRows = ref<AttributeRow[]>([])

const addAttributeRow = () => {
  attributeRows.value.push({ key: '', value: '' })
}

const removeAttributeRow = (index: number) => {
  attributeRows.value.splice(index, 1)
}

const syncAttributesFromForm = () => {
  const attrs = form.value.attributes ?? {}
  attributeRows.value = Object.entries(attrs).map(([key, value]) => ({
    key,
    value: String(value),
  }))
}

watch(showDialog, (visible) => {
  if (visible) {
    syncAttributesFromForm()
  }
})

const onSubmit = () => {
  form.value.attributes = Object.fromEntries(
    attributeRows.value
      .filter((row) => row.key.trim())
      .map((row) => [row.key.trim(), row.value.trim()]),
  )

  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
