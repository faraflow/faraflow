// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { listApiKeyInfo, type ApiKeyInfo } from '$lib/utils/api'

/**
 * Which API keys are set, fetched once from the backend and kept in the browser.
 *
 * Editors, the dashboard and the RAG page only need to know whether a key exists, so they share
 * this one answer instead of each asking the backend (and the Settings modal loads its own data
 * only when it is opened). Call `refresh()` after a key is saved or deleted.
 */
class ApiKeyStatusStore {
    /** Key name -> whether it is set. */
    configured = $state<Record<string, boolean>>({})
    /** When the answer was fetched (ms since epoch), or null if it has not been fetched yet. */
    loadedAt = $state<number | null>(null)
    /**
     * How long an answer stays valid, in ms (30 minutes). After that the next `ensureLoaded()`
     * asks the backend again. `null` means it never expires.
     */
    ttlMs: number | null = 30 * 60 * 1000

    private inflight: Promise<void> | null = null

    isStale(): boolean {
        if (this.loadedAt === null) return true
        return this.ttlMs !== null && Date.now() - this.loadedAt > this.ttlMs
    }

    isConfigured(name: string): boolean {
        return !!this.configured[name]
    }

    hasAnyKey(): boolean {
        return Object.values(this.configured).some(Boolean)
    }

    /** Fetch only if nothing is cached yet (or the cached answer has expired). */
    async ensureLoaded(): Promise<void> {
        if (!this.isStale()) return
        return this.refresh()
    }

    /** Always ask the backend. Concurrent calls share one request. */
    refresh(): Promise<void> {
        if (!this.inflight) {
            this.inflight = listApiKeyInfo()
                .then((info: ApiKeyInfo[]) => {
                    this.configured = Object.fromEntries(info.map((k) => [k.name, k.configured]))
                    this.loadedAt = Date.now()
                })
                .finally(() => {
                    this.inflight = null
                })
        }
        return this.inflight
    }
}

export const apiKeyStatus = new ApiKeyStatusStore()
