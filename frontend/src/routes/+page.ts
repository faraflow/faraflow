// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { redirect } from '@sveltejs/kit';

export function load() {
    throw redirect(307, '/dashboard');
}
