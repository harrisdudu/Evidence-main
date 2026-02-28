import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { createSelectors } from '@/lib/utils'

export type Theme = 'light' | 'dark' | 'system'
export type Language = 'en' | 'zh'
export type QueryMode = 'naive' | 'local' | 'global' | 'hybrid' | 'mix' | 'bypass'

interface SettingsState {
  theme: Theme
  language: Language
  apiKey: string
  currentTab: string
  enableHealthCheck: boolean
  backendMaxGraphNodes: number
  graphMaxNodes: number
  
  setTheme: (theme: Theme) => void
  setLanguage: (lang: Language) => void
  setApiKey: (key: string) => void
  setCurrentTab: (tab: string) => void
  setEnableHealthCheck: (enable: boolean) => void
  setBackendMaxGraphNodes: (max: number) => void
  setGraphMaxNodes: (max: number, force?: boolean) => void
}

const useSettingsStoreBase = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'system',
      language: 'en',
      apiKey: '',
      currentTab: 'documents',
      enableHealthCheck: true,
      backendMaxGraphNodes: 1000,
      graphMaxNodes: 1000,
      
      setTheme: (theme) => {
        set({ theme })
        if (theme === 'dark') {
          document.documentElement.classList.add('dark')
        } else if (theme === 'light') {
          document.documentElement.classList.remove('dark')
        } else {
          const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
          if (systemDark) {
            document.documentElement.classList.add('dark')
          } else {
            document.documentElement.classList.remove('dark')
          }
        }
      },
      
      setLanguage: (language) => set({ language }),
      setApiKey: (apiKey) => set({ apiKey }),
      setCurrentTab: (currentTab) => set({ currentTab }),
      setEnableHealthCheck: (enableHealthCheck) => set({ enableHealthCheck }),
      setBackendMaxGraphNodes: (backendMaxGraphNodes) => set({ backendMaxGraphNodes }),
      setGraphMaxNodes: (graphMaxNodes, force = false) =>
        set((state) => ({
          graphMaxNodes: force
            ? graphMaxNodes
            : Math.min(graphMaxNodes, state.backendMaxGraphNodes),
        })),
    }),
    {
      name: 'graphrag-settings',
      partialize: (state) => ({
        theme: state.theme,
        language: state.language,
        apiKey: state.apiKey,
        enableHealthCheck: state.enableHealthCheck,
        graphMaxNodes: state.graphMaxNodes,
      }),
    }
  )
)

export const useSettingsStore = createSelectors(useSettingsStoreBase)
