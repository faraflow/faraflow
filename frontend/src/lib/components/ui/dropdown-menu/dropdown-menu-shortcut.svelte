<!--
  Copyright 2026 Alokin LLC
  Generated from shadcn-svelte (https://www.shadcn-svelte.com), MIT License. The MIT notice is in NOTICE.
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import { type WithElementRef } from "bits-ui";
	import { cn } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLSpanElement>> = $props();
</script>

<span
	bind:this={ref}
	class={cn("ml-auto text-xs tracking-widest opacity-60", className)}
	{...restProps}
>
	{@render children?.()}
</span>
