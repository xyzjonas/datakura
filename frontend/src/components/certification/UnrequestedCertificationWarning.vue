<template>
  <div
    class="flex flex-col gap-2 rounded-xl border-2 border-negative bg-red-1 p-4"
    data-test="unrequested-certification-warning"
  >
    <div class="flex items-center gap-2 font-bold text-negative">
      <q-icon name="sym_o_warning" size="24px" />
      Certifikované zboží{{ code ? ` (${code})` : '' }}
    </div>
    <div class="text-sm">
      Objednávka certifikaci <strong>nepožaduje</strong>. Certifikované zboží je dražší - jeho
      vychystání zde je zbytečné plýtvání.
    </div>
    <q-checkbox
      v-model="confirmed"
      color="negative"
      label="Ano, opravdu chci vychystat certifikované zboží"
      data-test="confirm-unrequested-certification"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ code?: string | null }>()

const confirmed = defineModel<boolean>({ default: false })
</script>
