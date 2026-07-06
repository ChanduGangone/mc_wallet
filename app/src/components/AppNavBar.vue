<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'
import { useRouter, useRoute } from 'vue-router'

const store = useStore()
const router = useRouter()
const route = useRoute()

const user = computed(() => store.state.auth.user)
const initials = computed(() => {
  const name = user.value?.name || user.value?.email || '?'
  return name.trim().charAt(0).toUpperCase()
})

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: 'mdi-view-dashboard' },
  { to: '/transfer', label: 'Transfer', icon: 'mdi-bank-transfer' },
  { to: '/transactions', label: 'History', icon: 'mdi-history' },
  { to: '/profile', label: 'Profile', icon: 'mdi-account-circle' },
]

async function handleLogout() {
  await store.dispatch('auth/logout')
  router.push({ name: 'login' })
}
</script>

<template>
  <v-app-bar color="primary" flat elevation="1">
    <v-app-bar-title class="d-flex align-center">
      <v-icon icon="mdi-wallet" class="mr-2" />
      <span class="font-weight-bold">mc_wallet</span>
    </v-app-bar-title>

    <v-btn
      v-for="link in links"
      :key="link.to"
      :to="link.to"
      variant="text"
      :prepend-icon="link.icon"
      :class="{ 'v-btn--active-link': route.path === link.to }"
    >
      {{ link.label }}
    </v-btn>

    <v-spacer />

    <v-menu>
      <template #activator="{ props: menuProps }">
        <v-avatar
          v-bind="menuProps"
          color="primary-darken-1"
          size="36"
          class="mr-2 cursor-pointer"
        >
          <span class="text-body-2">{{ initials }}</span>
        </v-avatar>
      </template>
      <v-list density="compact" min-width="200">
        <v-list-item :title="user?.name || 'Account'" :subtitle="user?.email" />
        <v-divider />
        <v-list-item to="/profile" prepend-icon="mdi-account-circle-outline" title="Profile" />
        <v-list-item prepend-icon="mdi-logout" title="Logout" @click="handleLogout" />
      </v-list>
    </v-menu>
  </v-app-bar>
</template>

<style scoped>
.v-btn--active-link {
  opacity: 1;
  font-weight: 600;
  background-color: rgba(255, 255, 255, 0.14);
}
.cursor-pointer {
  cursor: pointer;
}
</style>
