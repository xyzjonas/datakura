<template>
  <q-layout view="lhh Lpr fff">
    <q-header v-if="!noLayout && !isLoading">
      <q-toolbar class="flex gap-5 p-3 items-center">
        <SearchInput v-model="search" class="w-[512px]" />
        <div class="ml-auto flex items-center gap-10">
          <CurrentSiteInfo />
          <LoginInfo />
        </div>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="isOpened"
      v-if="!noLayout && !isLoading"
      side="left"
      persistent
      class="text-white p-1 bg-dark-8"
    >
      <div class="flex flex-col h-full">
        <AppLogo class="mb-2 p-1" />
        <q-scroll-area class="flex-1 p-2">
          <q-list class="flex flex-col gap-1">
            <MenuList
              :items="[
                {
                  label: 'Domů',
                  icon: 'sym_o_space_dashboard',
                  routeName: 'home',
                },
              ]"
            />
            <q-item-label header class="text-gray-4">Produkty</q-item-label>
            <MenuList
              :items="[
                {
                  label: 'Produkty',
                  icon: 'sym_o_package_2',
                  routeName: 'products',
                  routeMatch: 'products,productDetail',
                },
                {
                  label: 'Skupiny',
                  icon: 'sym_o_flowchart',
                  routeName: 'productGroups',
                  routeMatch: 'productGroups,productGroupDetail',
                },
              ]"
            />
            <q-item-label header class="text-gray-4">Nákup / Prodej</q-item-label>
            <MenuList
              :items="[
                {
                  label: 'Objednávky',
                  icon: 'sym_o_receipt',
                  routeName: 'orders',
                  routeMatch: 'orders',
                },
                {
                  label: 'Faktury',
                  icon: 'sym_o_attach_money',
                  routeName: 'submissions',
                },
                {
                  label: 'Dobropisy',
                  icon: 'sym_o_undo',
                  routeName: 'submissions',
                },
                {
                  label: 'Kalkulace',
                  icon: 'sym_o_calculate',
                  routeName: 'submissions',
                },
              ]"
            />
            <q-item-label header class="text-gray-4">Sklad</q-item-label>
            <MenuList
              :items="[
                {
                  label: 'Skladová místa',
                  icon: 'sym_o_location_on',
                  routeName: 'warehouses',
                },
                {
                  label: 'Příjemky',
                  icon: 'sym_o_input',
                  routeName: 'warehouseInboundOrders',
                  routeMatch: 'warehouseInboundOrders,warehouseInboundOrderDetail',
                },
                {
                  label: 'Výdejky',
                  icon: 'sym_o_output',
                  routeName: 'submissions',
                },
              ]"
            />
            <q-item-label header class="text-gray-4">Zákazník</q-item-label>
            <MenuList
              :items="[
                {
                  label: 'Zákazníci',
                  icon: 'sym_o_contacts_product',
                  routeName: 'customers',
                  routeMatch: 'customers,customerDetail',
                },
              ]"
            />
            <q-item-label header class="text-gray-4">Nastavení</q-item-label>
            <MenuList
              :items="[
                {
                  label: 'Nastavení Aplikace',
                  icon: 'sym_o_settings_applications',
                  routeName: 'settings',
                  routeMatch: 'settings',
                },
              ]"
            />
          </q-list>
          <q-list class="flex flex-col gap-2"> </q-list>
        </q-scroll-area>

        <q-list class="flex flex-col gap-2">
          <q-item clickable v-ripple @click="toggle" dense class="rounded-md">
            <q-item-section avatar>
              <q-icon :name="isDark ? 'light_mode' : 'dark_mode'" />
            </q-item-section>

            <q-item-section>{{ isDark ? 'Light Mode' : 'Dark Mode' }}</q-item-section>
          </q-item>
        </q-list>
      </div>
    </q-drawer>

    <BackToTopFab />

    <q-page-container>
      <q-page v-if="isLoading" class="grid justify-center content-center text-center">
        <q-spinner size="86px" :thickness="2" color="primary"></q-spinner>
        <span class="text-primary text-xl mt-5">Načítám</span>
      </q-page>
      <q-page padding class="flex gap-2 flex-nowrap" v-else>
        <slot></slot>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { useDarkmode } from '@/composables/use-dark-mode'
import { useGlobalLoading } from '@/composables/use-global-loading'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppLogo from '../AppLogo.vue'
import LoginInfo from './LoginInfo.vue'
import MenuList from '../MenuList.vue'
import SearchInput from '../SearchInput.vue'
import BackToTopFab from './BackToTopFab.vue'
import CurrentSiteInfo from './CurrentSiteInfo.vue'

const search = ref('')
const { isDark, toggle } = useDarkmode()
const isOpened = ref(true)

const { currentRoute } = useRouter()
const noLayout = computed(() => currentRoute.value.meta.disableLayout === true)

const { isLoading } = useGlobalLoading()
</script>

<style lang="scss" scoped>
// :deep(a) {
//   color: white !important;
// }
</style>
