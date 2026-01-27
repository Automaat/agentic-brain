<script lang="ts">
	import { Card } from '@mskalski/home-ui';
	import type { ChatMessage } from '$lib/stores/chat';

	export let message: ChatMessage;

	$: isUser = message.role === 'user';
	$: variant = isUser ? 'blue' : 'default';
	$: className = isUser ? 'message-user' : 'message-assistant';
</script>

<div class={className}>
	<Card {variant}>
		<p>{message.content}</p>
	</Card>
</div>

<style>
	p {
		margin: 0;
		white-space: pre-wrap;
		word-wrap: break-word;
	}
</style>
