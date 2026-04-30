<template>
  <div class="flex-1 flex flex-col gap-4">
    <ForegroundPanel no-padding class="overflow-hidden">
      <div
        class="relative grid gap-6 overflow-hidden px-6 py-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(18rem,0.9fr)]"
      >
        <div class="absolute -right-12 -top-10 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
        <div class="absolute bottom-0 left-20 h-24 w-24 rounded-full bg-orange/10 blur-2xl" />

        <div class="relative flex flex-col gap-4">
          <div>
            <div class="text-xs font-semibold uppercase tracking-wide text-primary">
              Přehled skladu
            </div>
            <h1 class="mt-3 max-w-3xl text-3xl font-semibold leading-tight text-balance">
              Řízení zásob, objednávek a skladových pohybů na jednom místě.
            </h1>
            <p class="mt-3 max-w-2xl text-sm leading-6 text-gray-6">
              Sledujte hodnotu skladu, otevřené objednávky a aktivní příjemky nebo výdejky v jednom
              přehledu.
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <q-btn
              color="primary"
              unelevated
              icon="sym_o_receipt_long"
              label="Objednávky"
              :to="{ name: 'orders' }"
            />
            <q-btn
              color="grey-8"
              flat
              icon="sym_o_package_2"
              label="Produkty"
              :to="{ name: 'products' }"
            />
          </div>
        </div>
      </div>
    </ForegroundPanel>

    <div class="flex items-center justify-between gap-3">
      <div>
        <div class="text-xs font-semibold uppercase tracking-wide text-gray-5">Denní operativa</div>
        <h2 class="mt-1 text-xl font-semibold">Klíčové ukazatele skladu</h2>
      </div>
      <div class="text-sm text-gray-5">Rychlý přehled bez otevírání jednotlivých modulů.</div>
    </div>

    <div class="grid w-full gap-2 xl:grid-cols-2">
      <WarehouseValueWidget class="min-w-0" />
      <ActiveOrdersWidget class="min-w-0 min-h-30" />
    </div>
  </div>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import ActiveOrdersWidget from '@/components/widgets/ActiveOrdersWidget.vue'
import WarehouseValueWidget from '@/components/widgets/WarehouseValueWidget.vue'
</script>

<style></style>
