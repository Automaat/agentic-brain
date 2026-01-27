import { writable, get } from 'svelte/store';
import { sendMessage as apiSendMessage, getHistory, resetSession, type HistoryMessage } from '$lib/api/brain';
import { userId, sessionId, language } from './session';

export interface ChatMessage {
	role: 'user' | 'assistant';
	content: string;
	timestamp?: Date;
}

interface ChatState {
	messages: ChatMessage[];
	loading: boolean;
	error: string | null;
}

function createChatStore() {
	const { subscribe, set, update } = writable<ChatState>({
		messages: [],
		loading: false,
		error: null
	});

	return {
		subscribe,
		loadHistory: async (sid: string) => {
			try {
				const history = await getHistory(sid);
				const messages: ChatMessage[] = history.map((msg: HistoryMessage) => ({
					role: msg.role,
					content: msg.content,
					timestamp: new Date()
				}));
				update((state) => ({ ...state, messages, error: null }));
			} catch (error) {
				console.error('Failed to load history:', error);
				update((state) => ({ ...state, error: 'Failed to load history' }));
			}
		},
		sendMessage: async (content: string) => {
			const uid = get(userId);
			const sid = get(sessionId);
			const lang = get(language);

			update((state) => ({
				...state,
				messages: [...state.messages, { role: 'user', content, timestamp: new Date() }],
				loading: true,
				error: null
			}));

			try {
				const response = await apiSendMessage(content, uid, sid, lang);
				update((state) => ({
					...state,
					messages: [...state.messages, { role: 'assistant', content: response, timestamp: new Date() }],
					loading: false
				}));
			} catch (error) {
				console.error('Failed to send message:', error);
				update((state) => ({
					...state,
					loading: false,
					error: error instanceof Error ? error.message : 'Failed to send message'
				}));
			}
		},
		reset: async (sid: string) => {
			try {
				await resetSession(sid);
				set({
					messages: [],
					loading: false,
					error: null
				});
			} catch (error) {
				console.error('Failed to reset session:', error);
				update((state) => ({ ...state, error: 'Failed to reset session' }));
			}
		}
	};
}

export const chat = createChatStore();
