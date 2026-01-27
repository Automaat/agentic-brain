const baseUrl = import.meta.env.VITE_BRAIN_API_URL || '/api';

interface ChatRequest {
	message: string;
	interface: 'api';
	language: 'en' | 'pl';
}

interface ChatResponse {
	response: string;
	actions: [];
}

export interface HistoryMessage {
	role: 'user' | 'assistant';
	content: string;
}

export async function sendMessage(
	message: string,
	userId: string,
	sessionId: string,
	language: 'en' | 'pl' = 'pl'
): Promise<string> {
	const res = await fetch(`${baseUrl}/chat`, {
		method: 'POST',
		headers: {
			'user_id': userId,
			'session_id': sessionId,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			message,
			interface: 'api',
			language
		} as ChatRequest)
	});

	if (!res.ok) {
		throw new Error(`API error: ${res.status}`);
	}

	const data: ChatResponse = await res.json();
	return data.response;
}

export async function getHistory(sessionId: string): Promise<HistoryMessage[]> {
	const res = await fetch(`${baseUrl}/history/${sessionId}`);

	if (!res.ok) {
		if (res.status === 404) {
			return [];
		}
		throw new Error(`API error: ${res.status}`);
	}

	return res.json();
}

export async function resetSession(sessionId: string): Promise<void> {
	await fetch(`${baseUrl}/reset-session`, {
		method: 'POST',
		headers: {
			'session_id': sessionId,
			'Content-Type': 'application/json'
		}
	});
}
