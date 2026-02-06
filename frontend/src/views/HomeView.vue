<template>
  <div class="flex-1 flex flex-col gap-2">
    <!-- <div class="flex justify-center mt-5 mb-10">
      <h1>Vítejte!</h1>
      <span></span>
    </div> -->
    <div class="grid grid-cols-3 gap-2">
      <DemoGraphWidget
        title="123 591 CZK"
        subtitle="Obrat tento měsíc"
        data-key="sales"
        data-label="Obrat"
        x-axis-key="sales"
        color="#21a25b"
        :data="[
          { month: 'Jan', sales: 100 },
          { month: 'Feb', sales: 120 },
          { month: 'Mar', sales: 180 },
          { month: 'Apr', sales: 110 },
          { month: 'May', sales: 90 },
        ]"
      />
      <DemoGraphWidget
        title="12"
        subtitle="Aktivní objednávky"
        data-key="sales"
        data-label="Počet objednávek"
        x-axis-key="foo"
        color="#1976d2"
        :to="{ name: 'orders' }"
        :data="[
          { month: 'Jan', sales: 10 },
          { month: 'Feb', sales: 12 },
          { month: 'Mar', sales: 3 },
          { month: 'Apr', sales: 1 },
          { month: 'May', sales: 12 },
        ]"
      />
      <DemoGraphWidget
        title="12"
        subtitle="Aktivní výdejky a příjemky"
        data-key="sales"
        data-label="Počet výdejek a příjemek"
        x-axis-key="foo"
        color="#ff9800"
        :to="{ name: 'orders' }"
        :data="[
          { month: '8:00', sales: 80 },
          { month: '12:00', sales: 30 },
          { month: '16:00', sales: 44 },
          { month: '20:00', sales: 3 },
          { month: '24:00', sales: 10 },
        ]"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import DemoGraphWidget from '@/components/widgets/DemoGraphWidget.vue'
import { useTimestamp } from '@vueuse/core'

const {} = useTimestamp()
</script>

<style></style>
