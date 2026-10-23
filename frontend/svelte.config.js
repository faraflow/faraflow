// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
    preprocess: vitePreprocess(),
    kit: {
        adapter: adapter({
            // Single-page app fallback - all unmatched routes serve this file
            fallback: '200.html'
        }),
        alias: {
            '@': './src'
        }
    }
};

export default config;