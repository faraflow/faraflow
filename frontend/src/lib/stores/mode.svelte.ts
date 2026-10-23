// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
export type Mode = 'pointer' | 'hand' | 'select' | 'connect'

class ModeStore {
    mode = $state<Mode>('hand')

    setMode(mode: Mode) {
        this.mode = mode
    }
}

export const modeStore = new ModeStore()
