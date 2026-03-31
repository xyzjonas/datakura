<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-xl">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-start gap-2">
          <div class="flex flex-col flex-1">
            <span class="text-2xl uppercase">Přesunout do podřízené objednávky</span>
            <a class="link" @click="goToProduct(item.product.code)">{{ item.product.name }}</a>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <div class="text-gray-5 mt-3 mb-5">
          Zvolené množství bude přesunuto do nové (nebo existující) podřízené objednávky, čímž
          odblokuje zpracování nadřazené objednávky.
        </div>
        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-input
            v-model.number="amount"
            outlined
            label="Množství k přesunu"
            :rules="[
              rules.isNumber,
              rules.atLeastOne,
              (val) => val <= item.amount || `K dispozici je maximálně ${item.amount} jednotek`,
            ]"
          >
            <template #append>
              <span class="text-xs">{{ item.unit_of_measure }}</span>
            </template>
          </q-input>
          <div class="px-3">
            <q-slider
              v-model="amount"
              :markers="Math.ceil(item.amount / 10)"
              :min="0"
              :max="item.amount"
              marker-labels
              :step="item.amount > 50 ? 10 : 1"
            />
          </div>
          <q-btn
            type="submit"
            unelevated
            color="warning"
            label="Přesunout"
            class="h-[3rem] mt-3"
            :loading="loading"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { type WarehouseItemSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import { rules } from '@/utils/rules'
import { ref } from 'vue'

const { goToProduct } = useAppRouter()

const props = defineProps<{
  item: WarehouseItemSchema
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'confirm', itemId: number, amount: number): void
}>()

const showDialog = defineModel<boolean>('show', { default: false })

const amount = ref(props.item.amount)

const onSubmit = () => {
  emit('confirm', props.item.id, amount.value)
  showDialog.value = false
}
</script>
