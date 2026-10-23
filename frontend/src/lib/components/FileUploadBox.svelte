<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'

    interface Props {
        multiple?: boolean
        onFilesChange: (files: File[]) => void
        acceptedFileTypes?: Record<string, string[]>
        supportedFormatsMessage?: string
    }

    let {
        multiple = false,
        onFilesChange,
        acceptedFileTypes,
        supportedFormatsMessage = 'Drag & drop files here or click to browse',
    }: Props = $props()

    let isDragging = $state(false)
    let fileInputEl: HTMLInputElement | undefined = $state()
    let selectedFiles = $state<File[]>([])

    const acceptString = $derived(
        acceptedFileTypes ? Object.keys(acceptedFileTypes).join(',') : undefined
    )

    function handleFiles(files: FileList | null) {
        if (!files) return
        const fileArray = Array.from(files)
        selectedFiles = multiple ? [...selectedFiles, ...fileArray] : fileArray
        onFilesChange(selectedFiles)
    }

    function handleDragOver(e: DragEvent) {
        e.preventDefault()
        isDragging = true
    }

    function handleDragLeave() {
        isDragging = false
    }

    function handleDrop(e: DragEvent) {
        e.preventDefault()
        isDragging = false
        handleFiles(e.dataTransfer?.files ?? null)
    }

    function handleChange(e: Event) {
        handleFiles((e.target as HTMLInputElement).files)
    }

    function removeFile(index: number) {
        selectedFiles = selectedFiles.filter((_, i) => i !== index)
        onFilesChange(selectedFiles)
    }
</script>

<div class="space-y-2">
    <!-- Drop zone -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors
            {isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}"
        ondragover={handleDragOver}
        ondragleave={handleDragLeave}
        ondrop={handleDrop}
        onclick={() => fileInputEl?.click()}
        role="button"
        tabindex="0"
    >
        <Icon icon="solar:upload-linear" width={24} class="mx-auto mb-2 text-muted-foreground" />
        <p class="text-sm text-muted-foreground">{supportedFormatsMessage}</p>
        <input
            bind:this={fileInputEl}
            type="file"
            class="hidden"
            {multiple}
            accept={acceptString}
            onchange={handleChange}
        />
    </div>

    <!-- Selected files list -->
    {#if selectedFiles.length > 0}
        <ul class="space-y-1">
            {#each selectedFiles as file, i}
                <li class="flex items-center justify-between text-sm bg-muted/50 rounded px-2 py-1">
                    <span class="truncate mr-2">{file.name}</span>
                    <button
                        type="button"
                        class="text-muted-foreground hover:text-destructive shrink-0"
                        onclick={() => removeFile(i)}
                    >
                        <Icon icon="solar:close-circle-linear" width={14} />
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>
