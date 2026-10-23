// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
class PanelStore {
    isNodePanelExpanded = $state(false)
    bottomPanelHeight = $state(0)
    private _panToNode: ((nodeId: string) => void) | null = null

    setNodePanelExpanded(value: boolean) {
        this.isNodePanelExpanded = value
    }

    toggleNodePanelExpanded() {
        this.isNodePanelExpanded = !this.isNodePanelExpanded
    }

    registerPanToNode(fn: (nodeId: string) => void) {
        this._panToNode = fn
    }

    panToNode(nodeId: string) {
        this._panToNode?.(nodeId)
    }
}

export const panelStore = new PanelStore()
