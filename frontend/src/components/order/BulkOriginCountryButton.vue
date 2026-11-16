<template>
  <q-btn
    flat
    no-caps
    color="primary"
    icon="sym_o_public"
    :label="label"
    :disable="disabled"
    data-test="bulk-origin-country"
    @click="open = true"
  />

  <q-dialog v-model="open">
    <q-card class="w-full">
      <q-card-section class="flex items-start gap-2 pb-0">
        <div class="flex flex-col">
          <span class="text-xl uppercase">Země původu</span>
          <span class="text-gray-5 text-sm">{{ description }}</span>
        </div>
        <q-btn flat round dense icon="sym_o_close" v-close-popup class="ml-auto" />
      </q-card-section>
      <q-card-section>
        <CountrySelect v-model="country" autofocus />
      </q-card-section>
      <q-card-actions align="right" class="px-4 pb-4">
        <q-btn
          flat
          color="negative"
          label="vymazat u všech"
          data-test="bulk-origin-country-clear"
          @click="apply(null)"
        />
        <q-btn
          unelevated
          color="primary"
          label="použít na všechny"
          :disable="!country"
          data-test="bulk-origin-country-apply"
          @click="apply(country)"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import CountrySelect from '../selects/CountrySelect.vue'

withDefaults(
  defineProps<{
    disabled?: boolean
    label?: string
    description?: string
  }>(),
  {
    label: 'země původu pro vše',
    description: 'Nastaví zemi původu na všech položkách objednávky najednou.',
  },
)

const emit = defineEmits<{ (e: 'apply', country: string | null): void }>()

const open = ref(false)
const country = ref<string | null>(null)

watch(open, (isOpen) => {
  if (isOpen) country.value = null
})

const apply = (value: string | null) => {
  emit('apply', value)
  open.value = false
}
</script>
