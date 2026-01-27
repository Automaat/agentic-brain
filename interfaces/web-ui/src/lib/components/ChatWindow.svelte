<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { chat } from '$lib/stores/chat';
	import MessageBubble from './MessageBubble.svelte';

	let chatWindowElement: HTMLDivElement;

	function scrollToBottom() {
		if (chatWindowElement) {
			chatWindowElement.scrollTop = chatWindowElement.scrollHeight;
		}
	}

	afterUpdate(() => {
		scrollToBottom();
	});

	onMount(() => {
		scrollToBottom();
	});
</script>

<div class="chat-window" bind:this={chatWindowElement}>
	{#each $chat.messages as message}
		<MessageBubble {message} />
	{/each}
	{#if $chat.loading}
		<div class="loading-message">Myślę...</div>
	{/if}
	{#if $chat.error}
		<div class="error-message">{$chat.error}</div>
	{/if}
</div>

<style>
	.error-message {
		color: var(--color-danger, #dc3545);
		padding: var(--size-2, 0.5rem);
		text-align: center;
	}
</style>
