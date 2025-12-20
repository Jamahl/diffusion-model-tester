import { writable } from 'svelte/store';

export type ToastType = 'info' | 'success' | 'warning' | 'error';

export interface Toast {
    id: string;
    message: string;
    type: ToastType;
    duration?: number;
}

function createToastStore() {
    const { subscribe, update } = writable<Toast[]>([]);

    function add(message: string, type: ToastType = 'info', duration: number = 3000) {
        const id = Math.random().toString(36).substring(2, 9);
        update((toasts) => [...toasts, { id, message, type, duration }]);

        if (duration > 0) {
            setTimeout(() => {
                remove(id);
            }, duration);
        }
    }

    function remove(id: string) {
        update((toasts) => toasts.filter((t) => t.id !== id));
    }

    return {
        subscribe,
        add,
        remove,
        info: (m: string, d?: number) => add(m, 'info', d),
        success: (m: string, d?: number) => add(m, 'success', d),
        warning: (m: string, d?: number) => add(m, 'warning', d),
        error: (m: string, d?: number) => add(m, 'error', d),
    };
}

export const toasts = createToastStore();
