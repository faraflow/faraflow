// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
/**
 * Generic sidebar panel manager.
 *
 * Panels are declared in PANEL_ORDER from right-to-left (index 0 = rightmost).
 * To add a new panel, add its id to PANEL_ORDER — no offset math elsewhere.
 */

const STORAGE_KEY = 'faraflow_sidebar_panels'
const MIN_SIDEBAR_WIDTH = 200
const MAX_SIDEBAR_WIDTH = 800
const DEFAULT_SIDEBAR_WIDTH = 280

// Order = right-to-left (first entry = rightmost slot).
export const PANEL_ORDER = ['chat', 'runs', 'nodes'] as const
export type PanelId = (typeof PANEL_ORDER)[number]

class SidebarPanelStore {
    open = $state<Record<PanelId, boolean>>({ chat: true, runs: false, nodes: false })
    width = $state(DEFAULT_SIDEBAR_WIDTH)

    isOpen(id: PanelId): boolean {
        return this.open[id]
    }

    toggle(id: PanelId) {
        this.open[id] = !this.open[id]
        this.#save()
    }

    setWidth(w: number) {
        this.width = Math.max(MIN_SIDEBAR_WIDTH, Math.min(w, MAX_SIDEBAR_WIDTH))
        this.#save()
    }

    load() {
        if (typeof localStorage === 'undefined') return
        try {
            const raw = localStorage.getItem(STORAGE_KEY)
            if (!raw) return
            const parsed = JSON.parse(raw)
            for (const id of PANEL_ORDER) {
                if (typeof parsed[id] === 'boolean') this.open[id] = parsed[id]
            }
            if (typeof parsed.width === 'number') {
                this.width = Math.max(MIN_SIDEBAR_WIDTH, Math.min(parsed.width, MAX_SIDEBAR_WIDTH))
            }
        } catch {
            // ignore corrupt storage
        }
    }

    #save() {
        if (typeof localStorage === 'undefined') return
        const data = {
            ...Object.fromEntries(PANEL_ORDER.map((id) => [id, this.open[id]])),
            width: this.width,
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    }
}

export const sidebarPanels = new SidebarPanelStore()
