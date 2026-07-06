<script setup>
import { ref } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'

const store = useStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const errorMessage = ref('')
const loading = ref(false)

async function handleSubmit() {
  errorMessage.value = ''
  loading.value = true
  try {
    await store.dispatch('auth/login', { email: email.value, password: password.value })
    router.push({ name: 'dashboard' })
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Login failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-row justify="center" class="mt-12">
    <v-col cols="12" sm="7" md="4">
      <div class="text-center mb-6">
        <v-icon icon="mdi-wallet" size="48" color="primary" />
        <h1 class="text-h5 font-weight-bold mt-2">mc_wallet</h1>
        <p class="text-medium-emphasis">Welcome back — log in to continue</p>
      </div>
      <v-card>
        <v-card-text class="pa-6">
          <v-form @submit.prevent="handleSubmit">
            <v-text-field v-model="email" label="Email" type="email" prepend-inner-icon="mdi-email-outline" required />
            <v-text-field v-model="password" label="Password" type="password" prepend-inner-icon="mdi-lock-outline" required />
            <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
              {{ errorMessage }}
            </v-alert>
            <v-btn type="submit" color="primary" size="large" block :loading="loading">Log in</v-btn>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="justify-center pa-4">
          <span class="text-medium-emphasis">Don't have an account?</span>
          <v-btn to="/signup" variant="text" color="primary">Sign up</v-btn>
        </v-card-actions>
      </v-card>
    </v-col>
  </v-row>
</template>
