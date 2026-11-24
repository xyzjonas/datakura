<template>
  <div class="flex h-full min-h-60 flex-col gap-2 text-xs">
    <q-input v-model="search" dense outlined clearable placeholder="Hledat proměnnou / filtr…">
      <template #prepend><q-icon name="sym_o_search" /></template>
    </q-input>
    <p class="text-muted">
      Kliknutím vložíte do šablony. Položky seznamů (<code>[]</code>) se vkládají jako
      <code>{{ LOOP_VARIABLE }}</code> uvnitř cyklu <code>for</code>.
    </p>
    <div class="flex-1 overflow-auto rounded-md border border-solid border-gray-300">
      <h3 class="sticky top-0 bg-gray-100 px-2 py-1 font-semibold uppercase">Proměnné</h3>
      <button
        v-for="entry in fields"
        :key="entry.path"
        type="button"
        class="flex w-full items-baseline justify-between gap-2 border-0 bg-transparent px-2 py-1 text-left font-mono hover:bg-gray-100"
        :title="entry.description ?? undefined"
        @click="emit('insert', snippetFor(entry))"
      >
        <span class="break-all">{{ entry.path }}</span>
        <span class="shrink-0 text-muted">{{ entry.type }}</span>
      </button>
      <h3 class="sticky top-0 bg-gray-100 px-2 py-1 font-semibold uppercase">Filtry</h3>
      <button
        v-for="filter in filters"
        :key="filter.name"
        type="button"
        class="block w-full border-0 bg-transparent px-2 py-1 text-left hover:bg-gray-100"
        @click="emit('insert', `|${filter.name}`)"
      >
        <span class="font-mono">{{ filter.signature }}</span>
        <span class="block text-muted">{{ filter.description }}</span>
      </button>
      <p v-if="!fields.length && !filters.length" class="p-2 text-muted">Nic nenalezeno.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DocumentLegendSchema } from '@/client'
import { computed, ref } from 'vue'
import { LOOP_VARIABLE, snippetFor } from './template-snippets'

const props = defineProps<{ legend?: DocumentLegendSchema }>()
const emit = defineEmits<{ insert: [snippet: string] }>()

const search = ref<string | null>('')
const needle = computed(() => (search.value ?? '').trim().toLowerCase())

const fields = computed(() =>
  (props.legend?.fields ?? []).filter((f) => f.path.toLowerCase().includes(needle.value)),
)
const filters = computed(() =>
  (props.legend?.filters ?? []).filter(
    (f) =>
      f.name.toLowerCase().includes(needle.value) ||
      f.description.toLowerCase().includes(needle.value),
  ),
)
</script>
