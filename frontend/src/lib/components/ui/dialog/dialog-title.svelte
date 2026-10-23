<!--
  Copyright 2026 Alokin LLC
  Generated from shadcn-svelte (https://www.shadcn-svelte.com), MIT License. The MIT notice is in NOTICE.
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
	import { Dialog as DialogPrimitive } from "bits-ui";
	import { cn } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		...restProps
	}: DialogPrimitive.TitleProps = $props();
</script>

<DialogPrimitive.Title
	bind:ref
	class={cn("text-lg font-semibold leading-none tracking-tight", className)}
	{...restProps}
/>
