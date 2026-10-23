<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    interface Props {
        size?: 'sm' | 'md' | 'lg'
    }
    let { size = 'lg' }: Props = $props()
    const sizeClass = $derived(size === 'sm' ? 'h-4 w-4' : size === 'md' ? 'h-8 w-8' : 'h-32 w-32')
</script>

<div class="flex items-center justify-center h-full">
    <div class="animate-spin rounded-full {sizeClass} border-b-2 border-gray-900 dark:border-gray-100"></div>
</div>
