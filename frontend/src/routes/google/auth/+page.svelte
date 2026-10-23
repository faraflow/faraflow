<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { goto } from '$app/navigation'
    import { validateGoogleAccessToken } from '$lib/utils/api'
    onMount(async () => {
        try {
            const response = await validateGoogleAccessToken()
            if (response.is_valid) {
                goto('/')
            } else {
                oauthSignIn()
            }
        } catch {
            oauthSignIn()
        }
    })

    function oauthSignIn() {
        const oauth2Endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
        const baseUrl = window.location.origin

        const form = document.createElement('form')
        form.setAttribute('method', 'GET')
        form.setAttribute('action', oauth2Endpoint)

        const params: Record<string, string> = {
            client_id: (import.meta as any).env?.PUBLIC_GOOGLE_CLIENT_ID || '',
            redirect_uri: `${baseUrl}/google/callback`,
            scope: 'https://www.googleapis.com/auth/spreadsheets',
            include_granted_scopes: 'true',
            state: 'pass-through value',
            response_type: 'token',
        }

        for (const [key, value] of Object.entries(params)) {
            const input = document.createElement('input')
            input.setAttribute('type', 'hidden')
            input.setAttribute('name', key)
            input.setAttribute('value', value)
            form.appendChild(input)
        }

        document.body.appendChild(form)
        form.submit()
    }
</script>

<svelte:head>
    <title>Google Authentication - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex justify-center items-center">
    <p>Redirecting to Google for authentication...</p>
</div>
