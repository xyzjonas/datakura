<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-2xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-1 gap-2">
          <span class="text-2xl uppercase">Korekce hmotnosti a celního kódu</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <div class="text-sm text-muted mb-4">{{ product.name }} · {{ product.code }}</div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-input
            v-model.number="form.unit_weight"
            outlined
            type="number"
            min="0"
            step="0.01"
            label="Váha jednotky (kg)"
            hint="Hmotnost jedné jednotky v gramech"
            :rules="[rules.notEmpty, rules.weightPositive]"
          />
          <q-input
            v-model.trim="form.customs_declaration_group"
            outlined
            label="Celní nomenklatura"
            hint="Celní kód (nepovinné)"
            maxlength="255"
          />

          <q-separator />
          <div class="mt-2 flex justify-end">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              label="uložit"
              :loading="loading"
              class="h-[3rem] min-w-[10rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { ProductSchema } from '@/client'
import { warehouseApiRoutesProductUpdateProductCustomsWeight } from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import { useQuasar } from 'quasar'
import { reactive, ref, watch } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })

const props = defineProps<{
  product: Pick<ProductSchema, 'code' | 'name' | 'unit_weight' | 'customs_declaration_group'>
}>()

const emit = defineEmits<{
  (e: 'saved', product: ProductSchema): void
}>()

const $q = useQuasar()
const { onResponse } = useApi()
const loading = ref(false)

const form = reactive({
  unit_weight: props.product.unit_weight as number | null,
  customs_declaration_group: props.product.customs_declaration_group ?? '',
})

// Re-seed from the current product whenever the dialog opens; a missing weight starts empty
watch(showDialog, (visible) => {
  if (!visible) return
  form.unit_weight = props.product.unit_weight > 0 ? props.product.unit_weight : null
  form.customs_declaration_group = props.product.customs_declaration_group ?? ''
})

const onSubmit = async () => {
  loading.value = true
  try {
    const data = onResponse(
      await warehouseApiRoutesProductUpdateProductCustomsWeight({
        path: { product_code: props.product.code },
        body: {
          unit_weight: form.unit_weight as number,
          customs_declaration_group: form.customs_declaration_group || null,
        },
      }),
    )
    if (data?.data) {
      $q.notify({ type: 'positive', message: 'Hmotnost a celní kód uloženy', position: 'top' })
      showDialog.value = false
      emit('saved', data.data)
    }
  } finally {
    loading.value = false
  }
}
</script>
