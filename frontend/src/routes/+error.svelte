<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores';
</script>

<svelte:head>
    <title>Error — Faraflow</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-background">
    <div class="text-center">
        <h1 class="text-4xl font-bold text-foreground">{$page.status}</h1>
        <p class="mt-2 text-muted-foreground">{$page.error?.message ?? 'Something went wrong.'}</p>
        <a href="/dashboard" class="mt-6 inline-block text-primary underline underline-offset-4">
            Go to dashboard
        </a>
    </div>
</div>
