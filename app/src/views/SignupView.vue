<script setup>
import { ref } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
import CurrencySelect from '@/components/CurrencySelect.vue'

const store = useStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const name = ref('')
const defaultCurrency = ref('USD')
const errorMessage = ref('')
const loading = ref(false)

async function handleSubmit() {
  errorMessage.value = ''
  loading.value = true
  try {
    await store.dispatch('auth/signup', {
      email: email.value,
      password: password.value,
      name: name.value || undefined,
      default_currency: defaultCurrency.value,
    })
    router.push({ name: 'dashboard' })
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Signup failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-row justify="center" class="mt-12">
    <v-col cols="12" sm="7" md="4">
      <div class="text-center mb-6">
        <v-icon icon="mdi-wallet-plus" size="48" color="primary" />
        <h1 class="text-h5 font-weight-bold mt-2">Create your account</h1>
        <p class="text-medium-emphasis">A wallet in your chosen currency is created automatically</p>
      </div>
      <v-card>
        <v-card-text class="pa-6">
          <v-form @submit.prevent="handleSubmit">
            <v-text-field v-model="email" label="Email" type="email" prepend-inner-icon="mdi-email-outline" required />
            <v-text-field
              v-model="password"
              label="Password"
              type="password"
              prepend-inner-icon="mdi-lock-outline"
              hint="Minimum 8 characters"
              required
            />
            <v-text-field v-model="name" label="Name (optional)" prepend-inner-icon="mdi-account-outline" />
            <CurrencySelect v-model="defaultCurrency" label="Default currency" />
            <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
              {{ errorMessage }}
            </v-alert>
            <v-btn type="submit" color="primary" size="large" block :loading="loading">Sign up</v-btn>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="justify-center pa-4">
          <span class="text-medium-emphasis">Already have an account?</span>
          <v-btn to="/login" variant="text" color="primary">Log in</v-btn>
        </v-card-actions>
      </v-card>
    </v-col>
  </v-row>
</template>
