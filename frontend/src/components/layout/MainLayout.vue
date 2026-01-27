<template>
  <q-layout view="hhh Lpr fff">
    <q-header>
      <q-toolbar class="flex gap-5 p-3 items-center">
        <div class="flex items-center gap-3 flex-nowrap">
          <!-- <q-btn dense flat :icon="isOpened ? 'close' : 'menu'" @click="isOpened = !isOpened" /> -->
          <span class="h-[16px] w-[16px] light:bg-primary dark:bg-light ml-2"></span>
          <q-separator vertical class="my-3 bg-gray h-[1rem]" />
          <a href="/" class="mr-[96px] light:text-primary dark:text-light">
            <span class="font-bold">SKLAD</span>
          </a>
        </div>

        <SearchInput v-model="search" class="w-[512px]" />

        <div class="ml-auto flex gap-2 flex-nowrap">
          <div class="flex flex-col items-end flex-nowrap">
            <span class="light:text-primary font-bold dark:text-light">Jaroslav Novák</span>
            <span class="text-xs text-gray-5">Administrátor</span>
          </div>
          <q-avatar rounded size="36px" class="rounded-full">
            <img
              src="https://static.vecteezy.com/system/resources/thumbnails/029/640/896/small_2x/side-view-of-a-handsome-young-man-face-on-white-background-generative-ai-free-photo.jpeg"
            />
          </q-avatar>
        </div>
      </q-toolbar>
    </q-header>

    <q-drawer v-model="isOpened" side="left" :width="196" persistent class="text-gray-6 p-1">
      <div class="flex flex-col h-full">
        <q-scroll-area class="flex-1">
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
            <q-item-label header>Produkty</q-item-label>
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
            <q-item-label header>Nákup / Prodej</q-item-label>
            <MenuList
              :items="[
                {
                  label: 'Vydané Obj.',
                  icon: 'sym_o_shoppingmode',
                  routeName: 'incomingOrders',
                  routeMatch: 'incomingOrders,incomingOrderDetail',
                },
                {
                  label: 'Objednávky',
                  icon: 'sym_o_receipt',
                  routeName: 'outboundOrders',
                },
                {
                  label: 'Faktury',
                  icon: 'sym_o_receipt_long',
                  routeName: 'submissions',
                },
                {
                  label: 'Kalkulace',
                  icon: 'sym_o_calculate',
                  routeName: 'submissions',
                },
              ]"
            />
            <q-item-label header>Sklad</q-item-label>
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
            <q-item-label header>Zákazník</q-item-label>
            <MenuList
              :items="[
                {
                  label: 'Zákazník',
                  icon: 'sym_o_contacts_product',
                  routeName: 'customers',
                  routeMatch: 'customers,customerDetail',
                },
              ]"
            />
          </q-list>
          <!-- <q-expansion-item
            icon="sym_o_barcode_scanner"
            label="Sklad"
            header-class="rounded-md my-2"
            :content-inset-level="0.3"
            dense
          >
            <q-list class="flex flex-col gap-2">
              <MenuList
                inset
                :items="[
                  {
                    label: 'Lokace',
                    icon: 'sym_o_location_on',
                    routeName: 'warehouse',
                  },
                  {
                    label: 'Příjemky',
                    icon: 'sym_o_input',
                    routeName: 'submissions',
                  },
                  {
                    label: 'Výdejky',
                    icon: 'sym_o_output',
                    routeName: 'submissions',
                  },
                ]"
              />
            </q-list>
          </q-expansion-item> -->
          <q-list class="flex flex-col gap-2"> </q-list>
        </q-scroll-area>

        <q-list>
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
      <q-page padding class="flex gap-2 flex-nowrap">
        <slot></slot>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { useDarkmode } from '@/composables/use-dark-mode'
import { ref } from 'vue'
import MenuList from '../MenuList.vue'
import SearchInput from '../SearchInput.vue'
import BackToTopFab from './BackToTopFab.vue'

const search = ref('')
const { isDark, toggle } = useDarkmode()
const isOpened = ref(true)
</script>

<style lang="scss" scoped></style>
