import { writable } from 'svelte/store';
import { browser } from '$app/environment';

function createPersistedStore<T>(key: string, initialValue: T) {
	const stored = browser ? localStorage.getItem(key) : null;
	const initial = stored ? (JSON.parse(stored) as T) : initialValue;

	const store = writable<T>(initial);

	if (browser) {
		store.subscribe((value) => {
			localStorage.setItem(key, JSON.stringify(value));
		});
	}

	return store;
}

function generateId(): string {
	return crypto.randomUUID();
}

export const userId = createPersistedStore('brain-user-id', generateId());
export const sessionId = createPersistedStore('brain-session-id', generateId());
export const language = createPersistedStore<'en' | 'pl'>('brain-language', 'pl');
