import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { createSelectors } from '@/lib/utils'

interface AuthState {
  isAuthenticated: boolean
  isGuestMode: boolean
  token: string | null
  username: string | null
  coreVersion: string | null
  apiVersion: string | null
  webuiTitle: string | null
  webuiDescription: string | null
  
  login: (token: string, isGuest?: boolean, username?: string | null, coreVersion?: string | null, apiVersion?: string | null) => void
  logout: () => void
  setVersion: (coreVersion: string | null, apiVersion: string | null) => void
  setCustomTitle: (title: string | null, description: string | null) => void
}

const useAuthStoreBase = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      isGuestMode: false,
      token: null,
      username: null,
      coreVersion: null,
      apiVersion: null,
      webuiTitle: null,
      webuiDescription: null,
      
      login: (token, isGuest = false, username = null, coreVersion = null, apiVersion = null) =>
        set({
          isAuthenticated: true,
          isGuestMode: isGuest,
          token,
          username,
          coreVersion,
          apiVersion,
        }),
      
      logout: () =>
        set({
          isAuthenticated: false,
          isGuestMode: false,
          token: null,
          username: null,
        }),
      
      setVersion: (coreVersion, apiVersion) =>
        set({ coreVersion, apiVersion }),
      
      setCustomTitle: (title, description) =>
        set({ webuiTitle: title, webuiDescription: description }),
    }),
    {
      name: 'graphrag-auth',
      partialize: (state) => ({
        token: state.token,
        isGuestMode: state.isGuestMode,
        username: state.username,
        coreVersion: state.coreVersion,
        apiVersion: state.apiVersion,
      }),
    }
  )
)

export const useAuthStore = createSelectors(useAuthStoreBase)
