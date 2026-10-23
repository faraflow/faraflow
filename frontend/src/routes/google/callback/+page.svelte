<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { storeGoogleAccessToken } from '$lib/utils/api'

    let statusMessage = $state('Processing authentication...')
    let isError = $state(false)

    onMount(async () => {
        try {
            const hash = window.location.hash.substring(1)
            const params = new URLSearchParams(hash)

            const accessToken = params.get('access_token')
            const expiresIn = params.get('expires_in')

            if (!accessToken) {
                throw new Error('No access token found in the URL')
            }

            await storeGoogleAccessToken(accessToken, expiresIn ?? '')
            statusMessage = 'Token stored successfully! You may close this window.'
            window.close()
        } catch (error) {
            console.error('Error during authentication:', error)
            statusMessage = 'Authentication failed. Please try again.'
            isError = true
        }
    })
</script>

<svelte:head>
    <title>Google Authentication - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex justify-center items-center">
    <p class={isError ? 'text-destructive' : ''}>{statusMessage}</p>
</div>
