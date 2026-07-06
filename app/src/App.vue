<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import AppNavBar from '@/components/AppNavBar.vue'

const store = useStore()
const isAuthenticated = computed(() => store.getters['auth/isAuthenticated'])
</script>

<template>
  <v-app>
    <AppNavBar v-if="isAuthenticated" />
    <v-main>
      <v-container class="py-8" max-width="1100">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>
