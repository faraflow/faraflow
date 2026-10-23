<!--
  Copyright 2026 Alokin LLC
  Generated from shadcn-svelte (https://www.shadcn-svelte.com), MIT License. The MIT notice is in NOTICE.
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
	import { cn } from "$lib/utils.js";
	import { type WithElementRef } from "bits-ui";
	import type { HTMLAttributes } from "svelte/elements";

	let {
		ref = $bindable(null),
		class: className,
		inset,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		inset?: boolean;
	} = $props();
</script>

<div
	bind:this={ref}
	class={cn("px-2 py-1.5 text-sm font-semibold", inset && "pl-8", className)}
	{...restProps}
>
	{@render children?.()}
</div>
