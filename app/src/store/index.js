import { createStore } from 'vuex'
import auth from './modules/auth'
import wallets from './modules/wallets'

export default createStore({
  modules: {
    auth,
    wallets,
  },
})
