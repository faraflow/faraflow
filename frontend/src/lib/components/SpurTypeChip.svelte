<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { SpurType } from '$lib/types/api_types/workflowSchemas'

    interface Props {
        spurType: SpurType
        showText?: boolean
    }

    let { spurType, showText = true }: Props = $props()

    const config = $derived((() => {
        switch (spurType) {
            case SpurType.CHATBOT:
                return { text: 'Chatbot', icon: 'lucide:message-square' }
            case SpurType.WORKFLOW:
                return { text: 'Workflow', icon: 'lucide:workflow' }
            case SpurType.AGENT:
                return { text: 'Agent', icon: 'lucide:bot' }
            default:
                return { text: typeof spurType === 'string' ? spurType : 'Unknown', icon: 'lucide:help-circle' }
        }
    })())
</script>

<span
    class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-default-100 text-default-700 dark:bg-default-800 dark:text-default-200"
    title={!showText ? config.text : undefined}
>
    <Icon icon={config.icon} width={14} />
    {#if showText}{config.text}{/if}
</span>
