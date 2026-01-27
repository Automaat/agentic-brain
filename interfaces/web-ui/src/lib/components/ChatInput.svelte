<script lang="ts">
	import { Input, Button } from '@mskalski/home-ui';
	import { chat } from '$lib/stores/chat';

	let inputValue = '';

	function handleSend() {
		if (inputValue.trim() && !$chat.loading) {
			chat.sendMessage(inputValue.trim());
			inputValue = '';
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSend();
		}
	}
</script>

<div class="chat-input-container">
	<Input
		bind:value={inputValue}
		placeholder="Napisz wiadomość..."
		disabled={$chat.loading}
		on:keydown={handleKeydown}
	/>
	<Button variant="primary" on:click={handleSend} disabled={$chat.loading || !inputValue.trim()}>
		Wyślij
	</Button>
</div>
