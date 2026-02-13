<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-xl">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-start items-center mb-3 gap-2">
          <div class="flex flex-col">
            <span class="text-2xl uppercase">Evidovat položku</span>
            <a class="link" @click="goToProduct(item.product.code)">{{ item.product.name }}</a>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <!-- <ItemSelectByName v-model="newItem" :rules="[rules.notEmpty]" class="flex-1" />
          <PlaceSelect v-show="manualSearchItem" v-model="newPlace" :rules="[rules.notEmpty]" /> -->

          <q-select
            v-model="trackingType"
            outlined
            label="Způsob evidence"
            hint="Vyberte jakým způsobem bude položka evidována"
            :options="tracking_type_options"
            option-label="label"
            option-value="value"
          />

          <div v-if="helpText" class="bg-gray-2 p-4 rounded-lg my-1 shadow shadow-inset">
            {{ helpText }}
          </div>

          <q-input
            v-model="amount"
            outlined
            :label="`Množství`"
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
            ></q-slider>
          </div>

          <PackageTypeSearchSelect
            v-model="selectedPackage"
            v-if="trackingType.value == 'package'"
          />

          <div v-if="items.length > 0">
            <WarehouseItemPreviewRow :item="item" :index="0" :amount="amount" />
            <div class="flex w-full justify-center my-2">
              <q-icon name="sym_o_arrow_cool_down" size="20px" />
            </div>
            <WarehouseItemPreviewRow
              v-for="(item, index) in items"
              :index="index"
              :item="item"
              :key="item.product.code"
            />
          </div>

          <q-btn
            type="submit"
            unelevated
            color="primary"
            :label="trackingType.value ? 'evidovat' : 'ne-evidovat'"
            class="h-[3rem] mt-3"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesPackagingPackagePreview,
  type PackageTypeSchema,
  type WarehouseItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { computed, ref, watch } from 'vue'
import PackageTypeSearchSelect from '../selects/PackageTypeSearchSelect.vue'
import WarehouseItemPreviewRow from './WarehouseItemPreviewRow.vue'
import { rules } from '@/utils/rules'

const { onResponse } = useApi()
const { goToProduct } = useAppRouter()

export type TrackingType = 'package' | '' | 'batch' | 'piece'

const helpTextMapping: Record<TrackingType, string> = {
  '': 'Toto zboží sledujeme jen celkově - evidujeme kolik kusů máme na skladě, ale nezapisujeme, odkud konkrétní kusy přišly nebo kde přesně leží. Všechny kusy stejného produktu jsou pro nás zaměnitelné - při výdeji vezmeme jakýkoliv dostupný kus.',
  batch:
    'Určité zboží sledujeme po výrobních dávkách (šaržích). Každá dávka má své číslo. Zboží můžeme brát jen ze stejné dávky - nemůžeme míchat kusy z různých dávek dohromady. Díky tomu vždy víme, odkud dávka přišla a kde přesně ve skladu leží.',
  piece:
    'Každý kus má své vlastní jedinečné číslo (jako sériové číslo). Díky tomu u každého kusu víme, odkud přišel a kde přesně ve skladu se nachází. Žádné dva kusy nejsou zaměnitelné.',
  package:
    'Každé balení má své jedinečné číslo. Díky tomu u každého balení víme, odkud přišlo a kde přesně se nachází. Z balení můžeme brát zboží i po jednotlivých kusech - balení se tím zmenší, ale pořád ho sledujeme a víme, kolik v něm zbývá.',
}

const tracking_type_options: { label: string; value: TrackingType }[] = [
  {
    label: 'Volně skladem',
    value: '',
  },
  {
    label: 'Balení',
    value: 'package',
  },
  {
    label: 'Šarže',
    value: 'batch',
  },
  {
    label: 'Kusy',
    value: 'piece',
  },
]

const props = defineProps<{
  item: WarehouseItemSchema
  trackingTypeIn?: TrackingType
}>()

const trackingType = ref(
  tracking_type_options.find((opt) => opt.value === props.trackingTypeIn) ??
    tracking_type_options[0],
)
const helpText = computed(() => helpTextMapping[trackingType.value.value])

const amount = ref(props.item.amount)

const selectedPackage = ref<PackageTypeSchema>()

const showDialog = defineModel('show', { default: false })

const items = ref<WarehouseItemSchema[]>([])
const previewItems = async () => {
  if (!selectedPackage.value) {
    return
  }
  const result = await warehouseApiRoutesPackagingPackagePreview({
    body: {
      warehouse_item_id: props.item.id,
      amount: amount.value,
      package_name: selectedPackage.value?.name,
      product_code: props.item.product.code,
    },
  })
  const data = onResponse(result)
  if (data) {
    items.value = data.data
  }
}

watch([selectedPackage, amount], () => {
  if (selectedPackage.value) {
    previewItems()
  } else {
    items.value = []
  }
})

const emit = defineEmits<{
  (e: 'packaged', items: WarehouseItemSchema[]): void
}>()
const onSubmit = () => {
  if (!trackingType.value.value) {
    showDialog.value = false
    return
  }
  if (trackingType.value.value === 'package') {
    emit('packaged', items.value)
    return
  }
}
</script>
<style lang="css" scoped></style>
