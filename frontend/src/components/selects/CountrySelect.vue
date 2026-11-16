<template>
  <q-select
    v-model="modelValue"
    outlined
    use-input
    hide-selected
    fill-input
    input-debounce="0"
    clearable
    emit-value
    map-options
    option-value="code"
    option-label="name"
    clear-icon="sym_o_close_small"
    :label="label"
    :hint="hint"
    :options="options"
    :rules="rules"
    data-test="country-select"
    @filter="onFilter"
    @update:model-value="onSelect"
  >
    <template #prepend>
      <span v-if="modelValue" class="text-lg leading-none">{{ countryFlag(modelValue) }}</span>
      <q-icon v-else name="sym_o_public" />
    </template>
    <template #option="{ opt, itemProps }">
      <q-item v-bind="itemProps">
        <q-item-section avatar class="min-w-0 text-lg">{{ opt.flag }}</q-item-section>
        <q-item-section>{{ opt.name }}</q-item-section>
        <q-item-section side class="text-xs text-gray-5">{{ opt.code }}</q-item-section>
      </q-item>
    </template>
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné výsledky</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { countryFlag, countryOptions, filterCountries, type CountryOption } from '@/utils/countries'
import type { ValidationRule } from 'quasar'
import { ref } from 'vue'

withDefaults(
  defineProps<{
    label?: string
    hint?: string
    rules?: ValidationRule[]
  }>(),
  { label: 'Země původu', hint: undefined, rules: undefined },
)

/** ISO 3166-1 alpha-2 code, null = not set */
const modelValue = defineModel<string | null | undefined>()

const options = ref<CountryOption[]>(countryOptions())

const onFilter = (value: string, update: (cb: () => void) => void) => {
  update(() => {
    options.value = filterCountries(value)
  })
}

const onSelect = (value: string | null | undefined) => {
  modelValue.value = value ?? null
}
</script>
