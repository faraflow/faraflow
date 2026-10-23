<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onDestroy, onMount } from 'svelte'
    import { createEditor } from 'svelte-tiptap'
    import { Color } from '@tiptap/extension-color'
    import TextStyle from '@tiptap/extension-text-style'
    import Underline from '@tiptap/extension-underline'
    import StarterKit from '@tiptap/starter-kit'
    import { Markdown } from 'tiptap-markdown'
    import Icon from '@iconify/svelte'
    import { generateMessage } from '$lib/utils/api'
    import { apiKeyStatus } from '$lib/stores/apiKeyStatus.svelte'

    interface Props {
        nodeID: string
        fieldName: string
        content: string
        setContent: (content: string) => void
        isEditable?: boolean
        fullScreen?: boolean
        inputSchema?: string[]
        fieldTitle?: string
        disableFormatting?: boolean
        isTemplateEditor?: boolean
        readOnly?: boolean
        enableAIGeneration?: boolean
        messageType?: 'system' | 'user'
    }

    let {
        nodeID,
        fieldName,
        content: initialContent,
        setContent,
        isEditable = true,
        fullScreen = false,
        inputSchema = [],
        fieldTitle,
        disableFormatting = false,
        isTemplateEditor = false,
        readOnly = false,
        enableAIGeneration = false,
        messageType = 'user',
    }: Props = $props()

    // svelte-ignore state_referenced_locally
    let localContent = $state(initialContent)
    let isModalOpen = $state(false)
    let isAIModalOpen = $state(false)
    let description = $state('')
    let generationType = $state<'new' | 'enhance'>('new')
    let isGenerating = $state(false)
    let generationError = $state('')
    let hasOpenAIKey = $state(false)
    let selectedVariables = $state<string[]>([])
    let updateFromProp = $state(false)
    let editorHostRef = $state<HTMLDivElement | undefined>()
    let modalEditorRef = $state<HTMLDivElement | undefined>()

    function getExtensions() {
        if (disableFormatting) {
            return [
                StarterKit.configure({
                    heading: false,
                    bold: false,
                    italic: false,
                    bulletList: false,
                    orderedList: false,
                    code: false,
                    codeBlock: false,
                    blockquote: false,
                    strike: false,
                }),
                Markdown.configure({
                    html: false,
                    transformPastedText: true,
                    transformCopiedText: true,
                }),
            ]
        }
        return [
            Color.configure({ types: [TextStyle.name] }),
            TextStyle.configure(),
            StarterKit.configure({
                bulletList: { keepMarks: true, keepAttributes: false },
                orderedList: { keepMarks: true, keepAttributes: false },
            }),
            Underline,
            Markdown.configure({
                html: false,
                transformPastedText: true,
                transformCopiedText: true,
            }),
        ]
    }

    // svelte-ignore state_referenced_locally
    const editor = createEditor({
        extensions: getExtensions(),
        content: initialContent || '',
        editorProps: {
            attributes: {
                class: 'w-full bg-default-100 hover:bg-default-200 transition-colors min-h-[120px] max-h-[300px] overflow-y-auto resize-y rounded-lg px-3 py-2 text-foreground outline-none placeholder:text-foreground-500',
            },
        },
        parseOptions: { preserveWhitespace: 'full' },
        onUpdate: ({ editor }) => {
            if (updateFromProp) return
            const newContent = editor.storage.markdown?.getMarkdown() ?? ''
            localContent = newContent
            setContent(newContent)
        },
        autofocus: 'end',
    })

    // svelte-ignore state_referenced_locally
    const modalEditor = createEditor({
        extensions: getExtensions(),
        content: '',
        editorProps: {
            attributes: {
                class: 'w-full min-h-[50vh] overflow-y-auto px-3 py-2 text-foreground outline-none',
            },
        },
        parseOptions: { preserveWhitespace: 'full' },
        autofocus: 'end',
    })

    // Sync when content prop changes externally
    $effect(() => {
        const currentEditor = $editor
        if (currentEditor && initialContent !== localContent) {
            updateFromProp = true
            currentEditor.commands.setContent(initialContent || '')
            localContent = initialContent
            updateFromProp = false
        }
    })

    $effect(() => {
        $editor?.setEditable(isEditable && !readOnly, false)
    })

    $effect(() => {
        const ed = $editor
        if (!ed || !editorHostRef) return
        if (!editorHostRef.contains(ed.view.dom)) {
            editorHostRef.appendChild(ed.view.dom)
        }
    })

    $effect(() => {
        const ed = $modalEditor
        if (!ed || !modalEditorRef) return
        if (!modalEditorRef.contains(ed.view.dom)) {
            modalEditorRef.appendChild(ed.view.dom)
        }
    })

    function openModal() {
        const currentContent = $editor?.storage.markdown?.getMarkdown() ?? ''
        $modalEditor?.commands.setContent(currentContent || '')
        isModalOpen = true
    }

    function saveModal() {
        const saved = $modalEditor?.storage.markdown?.getMarkdown() ?? ''
        updateFromProp = true
        $editor?.commands.setContent(saved || '')
        localContent = saved
        updateFromProp = false
        setContent(saved)
        isModalOpen = false
    }

    onDestroy(() => {
        $editor?.destroy()
        $modalEditor?.destroy()
    })

    // Check for OpenAI key
    onMount(async () => {
        try {
            await apiKeyStatus.ensureLoaded()
            hasOpenAIKey = apiKeyStatus.isConfigured('OPENAI_API_KEY')
        } catch {
            hasOpenAIKey = false
        }
    })

    function activeEditor() {
        return isModalOpen ? $modalEditor : $editor
    }

    function insertVariable(variable: string) {
        activeEditor()?.chain().focus().insertContent(`{{${variable}}}`).run()
    }

    function insertAllVariables() {
        if (!inputSchema?.length) return
        const schemaObject = inputSchema.reduce(
            (acc, v) => { acc[v] = `{{${v}}}`; return acc },
            {} as Record<string, string>
        )
        activeEditor()?.chain().focus().insertContent(JSON.stringify(schemaObject, null, 2)).run()
    }

    async function handleGenerateMessage() {
        if (!description.trim()) {
            generationError = 'Please enter a description'
            return
        }
        isGenerating = true
        generationError = ''
        try {
            const response = await generateMessage({
                description,
                message_type: messageType,
                existing_message: generationType === 'enhance' ? localContent : undefined,
                available_variables: selectedVariables.length > 0 ? selectedVariables : undefined,
            })
            if (isModalOpen) {
                $modalEditor?.commands.setContent(response.message)
            } else {
                localContent = response.message
                setContent(response.message)
                $editor?.commands.setContent(response.message)
            }
            isAIModalOpen = false
            description = ''
            generationType = 'new'
            selectedVariables = []
        } catch (e: any) {
            generationError = e?.message || 'Failed to generate message'
        } finally {
            isGenerating = false
        }
    }

    function isActive(type: string) {
        return activeEditor()?.isActive(type) ?? false
    }
</script>

<div class="text-editor w-full">
    <!-- Toolbar -->
    <div class="px-2 py-2 rounded-t-lg flex flex-col gap-2 w-full bg-default-100 border-b border-default-200">
        {#if !disableFormatting}
            <div class="flex justify-between items-center w-full">
                <div class="flex items-center gap-1 flex-wrap">
                    <!-- Bold -->
                    <button
                        type="button"
                        class="p-1 rounded {isActive('bold') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                        onclick={() => $editor?.chain().focus().toggleBold().run()}
                        title="Bold"
                    >
                        <Icon icon="solar:text-bold-linear" width={16} />
                    </button>
                    <!-- Italic -->
                    <button
                        type="button"
                        class="p-1 rounded {isActive('italic') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                        onclick={() => $editor?.chain().focus().toggleItalic().run()}
                        title="Italic"
                    >
                        <Icon icon="solar:text-italic-linear" width={16} />
                    </button>
                    <!-- Underline -->
                    <button
                        type="button"
                        class="p-1 rounded {isActive('underline') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                        onclick={() => $editor?.chain().focus().toggleUnderline().run()}
                        title="Underline"
                    >
                        <Icon icon="solar:text-underline-linear" width={16} />
                    </button>
                    <!-- Bullet List -->
                    <button
                        type="button"
                        class="p-1 rounded {isActive('bulletList') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                        onclick={() => $editor?.chain().focus().toggleBulletList().run()}
                        title="Bullet List"
                    >
                        <Icon icon="solar:list-linear" width={16} />
                    </button>
                    <!-- Ordered List -->
                    <button
                        type="button"
                        class="p-1 rounded {isActive('orderedList') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                        onclick={() => $editor?.chain().focus().toggleOrderedList().run()}
                        title="Ordered List"
                    >
                        <Icon icon="solar:list-check-linear" width={16} />
                    </button>
                </div>
                <div class="flex items-center gap-1">
                    {#if enableAIGeneration && hasOpenAIKey}
                        <button
                            type="button"
                            class="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary/10 text-primary hover:bg-primary/20"
                            onclick={() => { isAIModalOpen = true; selectedVariables = inputSchema || [] }}
                        >
                            <Icon icon="solar:magic-stick-3-linear" width={14} />
                            AI
                        </button>
                    {/if}
                    {#if !fullScreen}
                        <button
                            type="button"
                            class="p-1 rounded hover:bg-default-200"
                            onclick={openModal}
                            title="Full Screen"
                        >
                            <Icon icon="solar:full-screen-linear" width={14} />
                        </button>
                    {/if}
                </div>
            </div>
        {:else}
            <div class="flex justify-end items-center gap-1">
                {#if enableAIGeneration && hasOpenAIKey}
                    <button
                        type="button"
                        class="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary/10 text-primary hover:bg-primary/20"
                        onclick={() => { isAIModalOpen = true; selectedVariables = inputSchema || [] }}
                    >
                        <Icon icon="solar:magic-stick-3-linear" width={14} />
                        AI
                    </button>
                {/if}
                {#if !fullScreen}
                    <button
                        type="button"
                        class="p-1 rounded hover:bg-default-200"
                        onclick={openModal}
                        title="Full Screen"
                    >
                        <Icon icon="solar:full-screen-linear" width={14} />
                    </button>
                {/if}
            </div>
        {/if}

        <!-- Variable buttons -->
        {#if isTemplateEditor}
            {#if !inputSchema || inputSchema.length === 0}
                <div class="flex items-center gap-1 text-sm text-foreground-500 px-1">
                    <Icon icon="solar:info-circle-linear" width={14} />
                    Connect nodes to use variables
                </div>
            {:else}
                <div class="flex flex-wrap gap-1">
                    <button
                        type="button"
                        class="p-1 rounded bg-primary/10 text-primary hover:bg-primary/20"
                        onclick={insertAllVariables}
                        title="Insert all variables as JSON"
                    >
                        <Icon icon="solar:document-add-linear" width={14} />
                    </button>
                    {#each inputSchema as variable}
                        <button
                            type="button"
                            class="px-2 py-0.5 text-xs rounded bg-primary/10 text-primary hover:bg-primary/20"
                            onclick={() => insertVariable(variable)}
                        >
                            {variable}
                        </button>
                    {/each}
                </div>
            {/if}
        {/if}
    </div>

    <!-- Editor Content -->
    <div class="border border-default-200 rounded-b-lg {readOnly ? 'opacity-75 cursor-not-allowed' : ''}">
        <div bind:this={editorHostRef}></div>
    </div>
</div>

<!-- Full-screen Modal -->
{#if isModalOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onclick={(e) => { if (e.target === e.currentTarget) isModalOpen = false }}
    >
        <div class="bg-background rounded-xl shadow-xl w-[90vw] max-w-5xl flex flex-col max-h-[90vh]">
            <div class="flex items-center justify-between px-6 py-4 border-b">
                <h2 class="text-lg font-semibold">{fieldTitle || fieldName}</h2>
                <button type="button" class="p-1 rounded hover:bg-default-100" onclick={() => isModalOpen = false}>
                    <Icon icon="solar:close-circle-linear" width={20} />
                </button>
            </div>
            <!-- Modal toolbar -->
            <div class="px-4 py-2 border-b flex flex-col gap-2">
                {#if !disableFormatting}
                    <div class="flex justify-between items-center w-full">
                        <div class="flex items-center gap-1 flex-wrap">
                            <button
                                type="button"
                                class="p-1 rounded {isActive('bold') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                                onclick={() => $editor?.chain().focus().toggleBold().run()}
                                title="Bold"
                            >
                                <Icon icon="solar:text-bold-linear" width={16} />
                            </button>
                            <button
                                type="button"
                                class="p-1 rounded {isActive('italic') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                                onclick={() => $editor?.chain().focus().toggleItalic().run()}
                                title="Italic"
                            >
                                <Icon icon="solar:text-italic-linear" width={16} />
                            </button>
                            <button
                                type="button"
                                class="p-1 rounded {isActive('underline') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                                onclick={() => $editor?.chain().focus().toggleUnderline().run()}
                                title="Underline"
                            >
                                <Icon icon="solar:text-underline-linear" width={16} />
                            </button>
                            <button
                                type="button"
                                class="p-1 rounded {isActive('bulletList') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                                onclick={() => $editor?.chain().focus().toggleBulletList().run()}
                                title="Bullet List"
                            >
                                <Icon icon="solar:list-linear" width={16} />
                            </button>
                            <button
                                type="button"
                                class="p-1 rounded {isActive('orderedList') ? 'bg-primary text-primary-foreground' : 'hover:bg-default-200'}"
                                onclick={() => $editor?.chain().focus().toggleOrderedList().run()}
                                title="Ordered List"
                            >
                                <Icon icon="solar:list-check-linear" width={16} />
                            </button>
                        </div>
                        {#if enableAIGeneration && hasOpenAIKey}
                            <button
                                type="button"
                                class="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary/10 text-primary hover:bg-primary/20"
                                onclick={() => { isAIModalOpen = true; selectedVariables = inputSchema || [] }}
                            >
                                <Icon icon="solar:magic-stick-3-linear" width={14} />
                                AI
                            </button>
                        {/if}
                    </div>
                {:else if enableAIGeneration && hasOpenAIKey}
                    <div class="flex justify-end">
                        <button
                            type="button"
                            class="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary/10 text-primary hover:bg-primary/20"
                            onclick={() => { isAIModalOpen = true; selectedVariables = inputSchema || [] }}
                        >
                            <Icon icon="solar:magic-stick-3-linear" width={14} />
                            AI
                        </button>
                    </div>
                {/if}
                {#if isTemplateEditor && inputSchema && inputSchema.length > 0}
                    <div class="flex flex-wrap gap-1">
                        <button
                            type="button"
                            class="p-1 rounded bg-primary/10 text-primary hover:bg-primary/20"
                            onclick={insertAllVariables}
                            title="Insert all variables as JSON"
                        >
                            <Icon icon="solar:document-add-linear" width={14} />
                        </button>
                        {#each inputSchema as variable}
                            <button
                                type="button"
                                class="px-2 py-0.5 text-xs rounded bg-primary/10 text-primary hover:bg-primary/20"
                                onclick={() => insertVariable(variable)}
                            >
                                {variable}
                            </button>
                        {/each}
                    </div>
                {/if}
            </div>
            <div class="flex-1 overflow-auto p-4">
                <div class="border border-default-200 rounded-lg min-h-[50vh]">
                    <div bind:this={modalEditorRef}></div>
                </div>
            </div>
            <div class="flex justify-end gap-2 px-6 py-4 border-t">
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg border hover:bg-default-100 text-sm"
                    onclick={() => isModalOpen = false}
                >
                    Cancel
                </button>
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:opacity-90"
                    onclick={saveModal}
                >
                    Save
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- AI Generation Modal -->
{#if isAIModalOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onclick={(e) => { if (e.target === e.currentTarget && !isGenerating) isAIModalOpen = false }}
    >
        <div class="bg-background rounded-xl shadow-xl w-[90vw] max-w-2xl flex flex-col max-h-[90vh]">
            <div class="flex items-center justify-between px-6 py-4 border-b">
                <h2 class="text-lg font-semibold">Generate Message</h2>
                {#if !isGenerating}
                    <button type="button" class="p-1 rounded hover:bg-default-100" onclick={() => isAIModalOpen = false}>
                        <Icon icon="solar:close-circle-linear" width={20} />
                    </button>
                {/if}
            </div>
            <div class="flex-1 overflow-auto p-6 space-y-4">
                <!-- Generation type -->
                <div class="flex gap-4">
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="radio" bind:group={generationType} value="new" disabled={isGenerating} />
                        <span class="text-sm">Create New</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="radio" bind:group={generationType} value="enhance" disabled={isGenerating || !localContent} />
                        <span class="text-sm">Enhance Existing</span>
                    </label>
                </div>

                <!-- Variables to include -->
                {#if inputSchema && inputSchema.length > 0}
                    <div>
                        <p class="text-sm font-medium mb-2">Include variables:</p>
                        <div class="flex flex-wrap gap-1">
                            {#each inputSchema as variable}
                                <label class="flex items-center gap-1 px-2 py-0.5 text-xs rounded border cursor-pointer {selectedVariables.includes(variable) ? 'bg-primary/10 border-primary text-primary' : 'border-default-200'}">
                                    <input
                                        type="checkbox"
                                        class="sr-only"
                                        checked={selectedVariables.includes(variable)}
                                        onchange={(e) => {
                                            if (e.currentTarget.checked) {
                                                selectedVariables = [...selectedVariables, variable]
                                            } else {
                                                selectedVariables = selectedVariables.filter(v => v !== variable)
                                            }
                                        }}
                                    />
                                    {variable}
                                </label>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Description -->
                <div>
                    <label class="block text-sm font-medium mb-1">
                        {generationType === 'new' ? 'Describe what to generate' : 'Describe how to enhance'}
                        <textarea
                            class="w-full rounded-lg border border-default-200 bg-default-50 px-3 py-2 text-sm resize-y min-h-[80px] focus:outline-none focus:border-primary"
                            placeholder={generationType === 'new'
                                ? 'Example: A system prompt for a customer service assistant'
                                : 'Example: Make it more concise and add a JSON output requirement'}
                            bind:value={description}
                            disabled={isGenerating}
                        ></textarea>
                    </label>
                </div>

                {#if generationError}
                    <div class="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">
                        <Icon icon="solar:danger-triangle-linear" width={16} />
                        {generationError}
                    </div>
                {/if}
            </div>
            <div class="flex justify-end gap-2 px-6 py-4 border-t">
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg border hover:bg-default-100 text-sm disabled:opacity-50"
                    disabled={isGenerating}
                    onclick={() => isAIModalOpen = false}
                >
                    Cancel
                </button>
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                    disabled={isGenerating}
                    onclick={handleGenerateMessage}
                >
                    {#if isGenerating}
                        <Icon icon="svg-spinners:ring-resize" width={16} />
                        Generating...
                    {:else}
                        <Icon icon="solar:magic-stick-3-linear" width={16} />
                        Generate
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    :global(.ProseMirror) {
        outline: none;
        min-height: 120px;
        padding: 0.5rem 0.75rem;
    }
    :global(.ProseMirror p) {
        margin: 0;
    }
    :global(.ProseMirror > * + *) {
        margin-top: 0.5rem;
    }
</style>
