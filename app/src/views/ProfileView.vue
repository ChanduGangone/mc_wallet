<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import CurrencySelect from '@/components/CurrencySelect.vue'

const store = useStore()
const user = computed(() => store.state.auth.user)

const name = ref('')
const defaultCurrency = ref(null)
const photoMode = ref('file') // 'file' | 'url'
const photoFile = ref(null)
const photoUrlInput = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const loading = ref(false)

const photoSrc = computed(() => {
  if (!user.value?.photo_url) return null
  if (user.value.photo_url.startsWith('http')) return user.value.photo_url
  return `${import.meta.env.VITE_API_BASE_URL}${user.value.photo_url}`
})

const initials = computed(() => (user.value?.name || user.value?.email || '?').trim().charAt(0).toUpperCase())

function hydrateForm() {
  if (!user.value) return
  name.value = user.value.name || ''
  defaultCurrency.value = user.value.default_currency
}

async function handleSubmit() {
  errorMessage.value = ''
  successMessage.value = ''
  loading.value = true
  try {
    const fields = { name: name.value, default_currency: defaultCurrency.value }
    const selectedFile = Array.isArray(photoFile.value) ? photoFile.value[0] : photoFile.value
    if (photoMode.value === 'file' && selectedFile) {
      fields.photoFile = selectedFile
    } else if (photoMode.value === 'url' && photoUrlInput.value) {
      fields.photo_url = photoUrlInput.value
    }
    await store.dispatch('auth/updateProfile', fields)
    photoFile.value = null
    photoUrlInput.value = ''
    successMessage.value = 'Profile updated.'
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Could not update profile.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!user.value) {
    await store.dispatch('auth/fetchCurrentUser')
  }
  hydrateForm()
})
</script>

<template>
  <v-row justify="center">
    <v-col cols="12" sm="9" md="6">
      <div class="mb-6">
        <h1 class="text-h5 font-weight-bold">Profile</h1>
        <p class="text-medium-emphasis">Manage your account details</p>
      </div>

      <v-card>
        <v-card-text class="pa-6">
          <div class="d-flex align-center mb-6">
            <v-avatar size="80" color="primary" class="mr-4">
              <v-img v-if="photoSrc" :src="photoSrc" />
              <span v-else class="text-h5 text-white">{{ initials }}</span>
            </v-avatar>
            <div>
              <div class="text-h6">{{ user?.name || 'Unnamed user' }}</div>
              <div class="text-medium-emphasis">{{ user?.email }}</div>
            </div>
          </div>

          <v-divider class="mb-6" />

          <v-form @submit.prevent="handleSubmit">
            <v-text-field :model-value="user?.email" label="Email" prepend-inner-icon="mdi-email-outline" disabled />
            <v-text-field v-model="name" label="Name" prepend-inner-icon="mdi-account-outline" />
            <CurrencySelect v-model="defaultCurrency" label="Default currency" />

            <v-radio-group v-model="photoMode" inline label="Photo" class="mt-2">
              <v-radio label="Upload file" value="file" />
              <v-radio label="Set URL" value="url" />
            </v-radio-group>
            <v-file-input
              v-if="photoMode === 'file'"
              v-model="photoFile"
              label="Photo file"
              accept="image/*"
              prepend-inner-icon="mdi-camera-outline"
              prepend-icon=""
            />
            <v-text-field v-else v-model="photoUrlInput" label="Photo URL" prepend-inner-icon="mdi-link-variant" />

            <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">{{ errorMessage }}</v-alert>
            <v-alert v-if="successMessage" type="success" density="compact" class="mb-4">{{ successMessage }}</v-alert>

            <v-btn type="submit" color="primary" size="large" prepend-icon="mdi-content-save-outline" :loading="loading">
              Save
            </v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
