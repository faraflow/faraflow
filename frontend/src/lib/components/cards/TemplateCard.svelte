<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { Button } from '$lib/components/ui/button'

    interface Props {
        title: string
        description: string
        features?: string[]
        onUse: () => void
    }

    let { title, description, features = [], onUse }: Props = $props()
</script>

<div class="relative w-full rounded-xl border border-border bg-card flex flex-col overflow-hidden">
    <div class="relative min-h-[160px] bg-gradient-to-br from-card to-muted/30 p-5 flex-1">
        <h2 class="text-lg font-semibold mb-1">{title}</h2>
        <p class="text-muted-foreground text-sm mb-3">{description}</p>
        {#if features.length > 0}
            <ul class="space-y-1">
                {#each features as feature}
                    <li class="flex items-center text-sm">
                        <Icon icon="solar:check-circle-linear" class="text-green-500 mr-2 shrink-0" width={14} />
                        {feature}
                    </li>
                {/each}
            </ul>
        {/if}
    </div>
    <div class="border-t border-border flex justify-end py-2 px-4">
        <Button variant="secondary" size="sm" onclick={onUse}>
            <Icon icon="lucide:copy" width={14} class="mr-1" />
            Use Template
        </Button>
    </div>
</div>
