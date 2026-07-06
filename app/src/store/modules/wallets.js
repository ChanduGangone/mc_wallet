import * as walletsApi from '@/api/wallets'
import * as transfersApi from '@/api/transfers'
import * as transactionsApi from '@/api/transactions'
import * as ratesApi from '@/api/exchangeRates'

export default {
  namespaced: true,
  state: () => ({
    wallets: [],
    transactions: [],
    transactionsMeta: { total: 0, limit: 20, offset: 0 },
    exchangeRates: null,
  }),
  mutations: {
    SET_WALLETS(state, wallets) {
      state.wallets = wallets
    },
    SET_TRANSACTIONS(state, { items, total, limit, offset }) {
      state.transactions = items
      state.transactionsMeta = { total, limit, offset }
    },
    SET_RATES(state, rates) {
      state.exchangeRates = rates
    },
    UPDATE_WALLET_BALANCE(state, { walletId, newBalance }) {
      const w = state.wallets.find((w) => w.wallet_id === walletId)
      if (w) w.balance = newBalance
    },
  },
  actions: {
    async fetchWallets({ commit }) {
      const wallets = await walletsApi.getWallets()
      commit('SET_WALLETS', wallets)
      return wallets
    },
    async creditWallet({ commit }, { walletId, amount, currency }) {
      const result = await walletsApi.credit(walletId, { amount, currency })
      commit('UPDATE_WALLET_BALANCE', { walletId, newBalance: result.new_balance })
      return result
    },
    async createTransfer({ dispatch }, payload) {
      const result = await transfersApi.createTransfer(payload)
      await dispatch('fetchWallets')
      return result
    },
    async fetchTransactions({ commit }, filters) {
      const data = await transactionsApi.getTransactions(filters)
      commit('SET_TRANSACTIONS', data)
      return data
    },
    async fetchExchangeRates({ commit }) {
      const rates = await ratesApi.getLatestRates()
      commit('SET_RATES', rates)
      return rates
    },
  },
  getters: {
    walletById: (state) => (id) => state.wallets.find((w) => w.wallet_id === id),
  },
}
