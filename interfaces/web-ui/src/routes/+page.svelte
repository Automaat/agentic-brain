<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, CardHeader, CardTitle, CardContent, Button } from '@mskalski/home-ui';
	import ChatWindow from '$lib/components/ChatWindow.svelte';
	import ChatInput from '$lib/components/ChatInput.svelte';
	import { sessionId } from '$lib/stores/session';
	import { chat } from '$lib/stores/chat';

	onMount(async () => {
		await chat.loadHistory($sessionId);
	});

	async function handleReset() {
		if (confirm('Wyczyścić historię rozmowy?')) {
			await chat.reset($sessionId);
		}
	}
</script>

<svelte:head>
	<title>Brain Chat</title>
</svelte:head>

<div class="container">
	<Card>
		<CardHeader>
			<CardTitle>Brain Chat</CardTitle>
			<div class="header-actions">
				<Button variant="danger" size="small" on:click={handleReset}>Wyczyść</Button>
			</div>
		</CardHeader>
		<CardContent>
			<ChatWindow />
			<ChatInput />
		</CardContent>
	</Card>
</div>
