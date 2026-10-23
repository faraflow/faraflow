<!--
  Copyright 2026 Alokin LLC
  Generated from shadcn-svelte (https://www.shadcn-svelte.com), MIT License. The MIT notice is in NOTICE.
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
	import { Separator as SeparatorPrimitive } from "bits-ui";
	import { cn } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		orientation = "horizontal",
		...restProps
	}: SeparatorPrimitive.RootProps = $props();
</script>

<SeparatorPrimitive.Root
	bind:ref
	class={cn(
		"bg-border shrink-0",
		orientation === "horizontal" ? "h-[1px] w-full" : "min-h-full w-[1px]",
		className
	)}
	{orientation}
	{...restProps}
/>
