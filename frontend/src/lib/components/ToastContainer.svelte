<script lang="ts">
    import { toasts } from "$lib/stores/toasts";
    import { flip } from "svelte/animate";
    import { fade, fly } from "svelte/transition";
</script>

<div class="toast toast-end toast-bottom z-[100] p-4">
    {#each $toasts as toast (toast.id)}
        <div
            animate:flip={{ duration: 300 }}
            in:fly={{ y: 20, duration: 300 }}
            out:fade={{ duration: 200 }}
            class="alert shadow-lg border-white/5 backdrop-blur-md bg-opacity-90 {toast.type ===
            'success'
                ? 'alert-success'
                : ''} {toast.type === 'error'
                ? 'alert-error'
                : ''} {toast.type === 'warning'
                ? 'alert-warning'
                : ''} {toast.type === 'info' ? 'alert-info' : ''}"
        >
            <div class="flex items-center gap-2">
                {#if toast.type === "success"}
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="stroke-current shrink-0 h-6 w-6"
                        fill="none"
                        viewBox="0 0 24 24"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        /></svg
                    >
                {:else if toast.type === "error"}
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="stroke-current shrink-0 h-6 w-6"
                        fill="none"
                        viewBox="0 0 24 24"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                        /></svg
                    >
                {:else if toast.type === "warning"}
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="stroke-current shrink-0 h-6 w-6"
                        fill="none"
                        viewBox="0 0 24 24"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        /></svg
                    >
                {:else}
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        class="stroke-current shrink-0 w-6 h-6"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        ></path></svg
                    >
                {/if}
                <span class="text-sm font-medium">{toast.message}</span>
            </div>
            <button
                onclick={() => toasts.remove(toast.id)}
                class="btn btn-ghost btn-xs btn-circle opacity-50 hover:opacity-100"
                >✕</button
            >
        </div>
    {/each}
</div>
