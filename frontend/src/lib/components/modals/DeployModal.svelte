<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import { flowStore } from '$lib/stores/flow.svelte'
    import type { TestInput } from '$lib/types/api_types/workflowSchemas'

    interface Props {
        isOpen: boolean
        onOpenChange: (open: boolean) => void
        workflowId: string | null
        testInput?: TestInput
    }

    let { isOpen, onOpenChange, workflowId, testInput }: Props = $props()

    type SupportedLanguage = 'shell' | 'python' | 'javascript' | 'typescript' | 'rust' | 'java' | 'cpp'

    let selectedLanguage = $state<SupportedLanguage>('python')
    let apiCallType = $state<'blocking' | 'non-blocking'>('non-blocking')

    const nodes = $derived(flowStore.nodes)
    const nodeConfigs = $derived(flowStore.nodeConfigs)
    const inputNode = $derived(nodes.find((n) => n.type === 'InputNode'))
    const workflowInputVariables = $derived(
        inputNode ? nodeConfigs[inputNode.id]?.output_schema ?? {} : {}
    )

    const apiEndpoint = $derived.by(() => {
        if (!workflowId) return ''
        const base = typeof window !== 'undefined' ? window.location.origin : ''
        return apiCallType === 'non-blocking'
            ? `${base}/api/wf/${workflowId}/start_run/?run_type=non_blocking`
            : `${base}/api/wf/${workflowId}/run/?run_type=blocking`
    })

    const statusEndpoint = $derived(
        typeof window !== 'undefined' ? `${window.location.origin}/api/runs/{run_id}/status/` : ''
    )

    const exampleRequestBody = $derived.by(() => {
        const inputTitle = inputNode?.data?.title ?? 'input'
        const inputVars = Object.keys(workflowInputVariables).reduce<Record<string, any>>(
            (acc, key) => {
                acc[key] = testInput?.hasOwnProperty(key)
                    ? (testInput as any)[key]
                    : workflowInputVariables[key]?.type === 'number'
                      ? 0
                      : workflowInputVariables[key]?.type === 'boolean'
                        ? false
                        : 'example_value'
                return acc
            },
            {}
        )
        return { initial_inputs: { [inputTitle]: inputVars } }
    })

    function getCodeExample(lang: SupportedLanguage): string {
        const endpoint = apiEndpoint
        const body = JSON.stringify(exampleRequestBody, null, 2)
        const bodyInline = JSON.stringify(exampleRequestBody)

        const examples: Record<SupportedLanguage, string> = {
            shell: `curl -X POST ${endpoint} \\
  -H "Content-Type: application/json" \\
  -d '${body}'`,
            python: `import requests

url = '${endpoint}'
data = ${body}

response = requests.post(url, json=data)
print(response.status_code)
print(response.json())`,
            javascript: `fetch('${endpoint}', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(${bodyInline})
})
  .then(r => r.json())
  .then(data => console.log(data));`,
            typescript: `async function runWorkflow() {
  const response = await fetch('${endpoint}', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(${bodyInline})
  });
  const data = await response.json();
  console.log(data);
}`,
            rust: `use reqwest;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let response = client
        .post("${endpoint}")
        .json(&${bodyInline})
        .send()
        .await?;
    println!("{}", response.text().await?);
    Ok(())
}`,
            java: `import java.net.http.*;
import java.net.URI;

public class WorkflowClient {
    public static void main(String[] args) throws Exception {
        String body = ${JSON.stringify(bodyInline)};
        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("${endpoint}"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .build();
        HttpResponse<String> r = client.send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println(r.body());
    }
}`,
            cpp: `#include <cpr/cpr.h>
#include <iostream>

int main() {
    cpr::Response r = cpr::Post(
        cpr::Url{"${endpoint}"},
        cpr::Header{{"Content-Type", "application/json"}},
        cpr::Body{R"(${bodyInline})"});
    std::cout << r.text << std::endl;
    return 0;
}`,
        }
        return examples[lang]
    }

    function getStatusCheckExample(lang: SupportedLanguage): string {
        const endpoint = statusEndpoint.replace('{run_id}', 'YOUR_RUN_ID')
        const examples: Record<SupportedLanguage, string> = {
            shell: `curl ${endpoint}`,
            python: `import requests
response = requests.get('${endpoint}')
print(response.json())`,
            javascript: `fetch('${endpoint}')
  .then(r => r.json())
  .then(data => console.log(data));`,
            typescript: `const response = await fetch('${endpoint}');
const data = await response.json();
console.log(data);`,
            rust: `let response = client.get("${endpoint}").send().await?;
println!("{}", response.text().await?);`,
            java: `HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("${endpoint}"))
    .GET().build();
HttpResponse<String> r = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(r.body());`,
            cpp: `cpr::Response r = cpr::Get(cpr::Url{"${endpoint}"});
std::cout << r.text << std::endl;`,
        }
        return examples[lang]
    }

    // Close on Escape
    $effect(() => {
        if (!isOpen) return
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === 'Escape') onOpenChange(false)
        }
        window.addEventListener('keydown', onKeyDown)
        return () => window.removeEventListener('keydown', onKeyDown)
    })

    const languages: SupportedLanguage[] = ['shell', 'python', 'javascript', 'typescript', 'rust', 'java', 'cpp']
</script>

<Dialog.Root
    open={isOpen}
    onOpenChange={(open) => { if (!open) onOpenChange(false) }}
>
    <Dialog.Content class="max-w-4xl max-h-[90vh] flex flex-col p-0">
        <Dialog.Header class="px-6 py-4 border-b shrink-0">
            <Dialog.Title>API Endpoint Information</Dialog.Title>
        </Dialog.Header>

        <div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            <!-- Controls -->
            <div class="flex flex-wrap items-center gap-4">
                <div class="flex items-center gap-2">
                    <span class="text-sm">API call type:</span>
                    <select
                        class="text-sm border border-border rounded-md px-2 py-1 bg-background"
                        bind:value={apiCallType}
                    >
                        <option value="non-blocking">Non-blocking</option>
                        <option value="blocking">Blocking</option>
                    </select>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-sm">Language:</span>
                    <select
                        class="text-sm border border-border rounded-md px-2 py-1 bg-background"
                        bind:value={selectedLanguage}
                    >
                        {#each languages as lang}
                            <option value={lang}>{lang.charAt(0).toUpperCase() + lang.slice(1)}</option>
                        {/each}
                    </select>
                </div>
            </div>

            <!-- Example request -->
            <div>
                <div class="flex items-center justify-between mb-2">
                    <p class="text-sm font-medium">Example request:</p>
                    <Button
                        variant="ghost"
                        size="icon"
                        class="h-7 w-7"
                        title="Copy to clipboard"
                        onclick={() => navigator.clipboard.writeText(getCodeExample(selectedLanguage))}
                    >
                        <Icon icon="solar:copy-linear" width={14} />
                    </Button>
                </div>
                <pre class="bg-[#282c34] text-[#abb2bf] rounded-lg p-4 text-xs overflow-x-auto whitespace-pre font-mono">{getCodeExample(selectedLanguage)}</pre>
            </div>

            <!-- Status check (non-blocking only) -->
            {#if apiCallType === 'non-blocking'}
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <p class="text-sm font-medium">Check run status:</p>
                        <Button
                            variant="ghost"
                            size="icon"
                            class="h-7 w-7"
                            title="Copy to clipboard"
                            onclick={() => navigator.clipboard.writeText(getStatusCheckExample(selectedLanguage))}
                        >
                            <Icon icon="solar:copy-linear" width={14} />
                        </Button>
                    </div>
                    <pre class="bg-[#282c34] text-[#abb2bf] rounded-lg p-4 text-xs overflow-x-auto whitespace-pre font-mono">{getStatusCheckExample(selectedLanguage)}</pre>
                </div>
            {/if}
        </div>

        <div class="px-6 py-4 border-t shrink-0 flex justify-end">
            <Button onclick={() => onOpenChange(false)}>
                Close
                <span class="ml-1 text-xs opacity-60">ESC</span>
            </Button>
        </div>
    </Dialog.Content>
</Dialog.Root>
