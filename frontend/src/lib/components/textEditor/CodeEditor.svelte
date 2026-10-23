<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onDestroy } from 'svelte'
    import { EditorView } from 'codemirror'
    import { json } from '@codemirror/lang-json'
    import { python } from '@codemirror/lang-python'
    import { syntaxTree } from '@codemirror/language'
    import { linter } from '@codemirror/lint'
    import type { Diagnostic } from '@codemirror/lint'
    import { oneDark } from '@codemirror/theme-one-dark'
    import { EditorState, type Extension } from '@codemirror/state'
    import { keymap, lineNumbers, highlightActiveLineGutter } from '@codemirror/view'
    import { defaultKeymap, history, historyKeymap } from '@codemirror/commands'
    import { closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete'
    import Icon from '@iconify/svelte'

    interface Props {
        code: string
        label?: string
        onChange: (value: string) => void
        disabled?: boolean
        mode?: 'json' | 'python' | 'javascript'
        readOnly?: boolean
        height?: string
    }

    let {
        code,
        onChange,
        disabled = false,
        mode = 'javascript',
        label = 'Code Editor',
        readOnly = false,
        height = '200px',
    }: Props = $props()

    let editorEl: HTMLDivElement
    let modalEditorEl = $state<HTMLDivElement | undefined>()
    let view: EditorView | null = null
    let modalView: EditorView | null = null
    let isModalOpen = $state(false)
    let modalValue = $state('')

    const jsonErrorTheme = EditorView.baseTheme({
        '.cm-json-error': {
            backgroundColor: '#ff000020',
            borderBottom: '2px wavy #ff0000',
        },
    })

    function jsonLinter() {
        return linter((view) => {
            if (mode !== 'json') return []
            const doc = view.state.doc.toString()
            try {
                JSON.parse(doc)
                return []
            } catch (e: any) {
                const message = e.message
                const match = /at position (\d+)/.exec(message)
                let pos = match ? parseInt(match[1]) : 0
                const tree = syntaxTree(view.state)
                const node = tree.resolve(pos, 1)
                const start = node.from
                const end = node.to
                if (start === end) {
                    const line = view.state.doc.lineAt(pos)
                    return [{ from: line.from, to: line.to, severity: 'error', message, markClass: 'cm-json-error' }]
                }
                return [{ from: start, to: end, severity: 'error', message, markClass: 'cm-json-error' }]
            }
        })
    }

    function getExtensions(isReadOnly: boolean): Extension[] {
        const exts: Extension[] = [
            oneDark,
            history(),
            keymap.of([...defaultKeymap, ...historyKeymap, ...closeBracketsKeymap]),
            closeBrackets(),
            lineNumbers(),
            highlightActiveLineGutter(),
            EditorView.editable.of(!isReadOnly && !disabled),
            EditorState.readOnly.of(isReadOnly || disabled),
            EditorView.lineWrapping,
        ]
        if (mode === 'json') {
            exts.push(json(), jsonLinter(), jsonErrorTheme)
        } else if (mode === 'python') {
            exts.push(python())
        }
        return exts
    }

    function createView(container: HTMLDivElement, initialDoc: string, onChangeCallback?: (val: string) => void) {
        const updateListener = EditorView.updateListener.of((update) => {
            if (update.docChanged && onChangeCallback) {
                onChangeCallback(update.state.doc.toString())
            }
        })
        return new EditorView({
            doc: initialDoc,
            extensions: [...getExtensions(onChangeCallback === undefined), updateListener],
            parent: container,
        })
    }

    $effect(() => {
        if (editorEl && !view) {
            view = createView(editorEl, code, (val) => {
                onChange(val)
            })
        }
    })

    $effect(() => {
        if (view) {
            const current = view.state.doc.toString()
            if (current !== code) {
                view.dispatch({
                    changes: { from: 0, to: current.length, insert: code },
                })
            }
        }
    })

    $effect(() => {
        if (isModalOpen && modalEditorEl && !modalView) {
            modalValue = code
            modalView = createView(modalEditorEl, modalValue, (val) => {
                modalValue = val
            })
        }
        if (!isModalOpen && modalView) {
            modalView.destroy()
            modalView = null
        }
    })

    function openModal() {
        if (readOnly || disabled) return
        isModalOpen = true
    }

    function closeModal(save: boolean) {
        if (save && modalView) {
            const newVal = modalView.state.doc.toString()
            onChange(newVal)
        }
        isModalOpen = false
    }

    onDestroy(() => {
        view?.destroy()
        modalView?.destroy()
    })
</script>

<div class="code-editor w-full relative">
    {#if label}
        <span class="text-sm font-semibold mb-2 block">{label}</span>
    {/if}
    {#if !readOnly && !disabled}
        <button
            type="button"
            class="absolute top-0 right-0 z-10 p-1 rounded hover:bg-default-100 cursor-pointer"
            onclick={openModal}
        >
            <Icon icon="solar:full-screen-linear" width={16} />
        </button>
    {/if}
    <div
        bind:this={editorEl}
        class="border rounded overflow-hidden {readOnly || disabled ? 'cursor-not-allowed opacity-75' : ''}"
        style="height: {height}; overflow-y: auto;"
    ></div>
</div>

{#if isModalOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onclick={(e) => { if (e.target === e.currentTarget) closeModal(false) }}
    >
        <div class="bg-background rounded-xl shadow-xl w-[90vw] max-w-5xl flex flex-col max-h-[90vh]">
            <div class="flex items-center justify-between px-6 py-4 border-b">
                <h2 class="text-lg font-semibold">{label}</h2>
                <button
                    type="button"
                    class="p-1 rounded hover:bg-default-100"
                    onclick={() => closeModal(false)}
                >
                    <Icon icon="solar:close-circle-linear" width={20} />
                </button>
            </div>
            <div class="flex-1 overflow-auto p-4">
                <div bind:this={modalEditorEl} class="border rounded" style="min-height: 60vh;"></div>
            </div>
            <div class="flex justify-end gap-2 px-6 py-4 border-t">
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg border hover:bg-default-100 text-sm"
                    onclick={() => closeModal(false)}
                >
                    Cancel
                </button>
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:opacity-90"
                    onclick={() => closeModal(true)}
                >
                    Save
                </button>
            </div>
        </div>
    </div>
{/if}
