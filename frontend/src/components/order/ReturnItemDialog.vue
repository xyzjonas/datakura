<template>
  <q-dialog v-model="show" @before-show="draft = amount || max">
    <q-card class="w-full max-w-md">
      <q-card-section class="flex items-start gap-2 pb-0">
        <div class="flex flex-col">
          <span class="text-xl uppercase">Vrátit zboží</span>
          <span class="text-gray-5 text-sm">{{ item.product.name }}</span>
        </div>
        <q-btn flat round dense icon="sym_o_close" v-close-popup class="ml-auto" />
      </q-card-section>
      <q-card-section class="flex flex-col gap-2">
        <q-input
          v-model.number="draft"
          type="number"
          outlined
          autofocus
          label="Vrácené množství"
          :suffix="item.product.unit"
          :min="0"
          :max="max"
          :error="!valid"
          :error-message="`Zadejte množství v rozmezí 0 - ${max}`"
          data-test="return-amount-input"
          @keyup.enter="confirm"
        />
        <div class="flex items-center justify-between text-sm text-gray-5">
          <span>K vrácení zbývá {{ max }} {{ item.product.unit }}</span>
          <span class="link" data-test="return-all" @click="draft = max">vrátit vše</span>
        </div>
      </q-card-section>
      <q-card-actions align="right" class="px-4 pb-4">
        <q-btn flat color="negative" label="zrušit" v-close-popup />
        <q-btn
          unelevated
          color="primary"
          label="přidat do vratky"
          :disable="!valid"
          data-test="return-confirm"
          @click="confirm"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  item: { product: { name: string; unit: string } }
  /** Most that can still be taken back. */
  max: number
}>()

const show = defineModel<boolean>('show', { default: false })
/** Amount of the row in the (not yet applied) return; 0 = not returned. */
const amount = defineModel<number>('amount', { default: 0 })

const draft = ref<number>(amount.value || props.max)
const valid = computed(() => Number(draft.value) > 0 && Number(draft.value) <= props.max)

const confirm = () => {
  if (!valid.value) {
    return
  }
  amount.value = Number(draft.value)
  show.value = false
}
</script>
