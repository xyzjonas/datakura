<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-start items-center mb-3 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <slot></slot>
        <div class="flex justify-end gap-2 mt-8">
          <q-btn
            label="potvrdit"
            @click="$emit('confirm')"
            unelevated
            outline
            color="primary"
            v-close-popup
          ></q-btn>
          <q-btn label="zrušit" @click="showDialog = false" flat color="negative"></q-btn>
        </div>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
const showDialog = defineModel('show', { default: false })

type Props = {
  title: string
}

defineProps<Props>()
defineEmits(['confirm'])
</script>
