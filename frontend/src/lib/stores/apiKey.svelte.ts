// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { PersistedState } from 'runed'

export const apiKey = new PersistedState<string>('faraflow_api_key', '')
