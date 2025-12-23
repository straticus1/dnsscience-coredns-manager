import { create } from 'zustand'

interface Store {
  resolver: 'coredns' | 'unbound'
  setResolver: (resolver: 'coredns' | 'unbound') => void
}

export const useStore = create<Store>((set) => ({
  resolver: 'coredns',
  setResolver: (resolver) => set({ resolver }),
}))
