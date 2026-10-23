// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
const STORAGE_KEY = 'faraflow_preferences'

class PreferencesStore {
    hasSeenWelcome = $state(false)

    markWelcomeSeen() {
        this.hasSeenWelcome = true
        this.#save()
    }

    load() {
        if (typeof localStorage === 'undefined') return
        try {
            const raw = localStorage.getItem(STORAGE_KEY)
            if (raw) {
                const parsed = JSON.parse(raw)
                this.hasSeenWelcome = parsed.hasSeenWelcome ?? false
            }
        } catch {
            // ignore corrupt storage
        }
    }

    #save() {
        if (typeof localStorage === 'undefined') return
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            hasSeenWelcome: this.hasSeenWelcome,
        }))
    }
}

export const preferencesStore = new PreferencesStore()
