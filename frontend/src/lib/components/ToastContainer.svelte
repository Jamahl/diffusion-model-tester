<script lang="ts">
    import { toasts } from "$lib/stores/toasts";
    import { flip } from "svelte/animate";
    import { fade, fly } from "svelte/transition";
</script>

<div
    class="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 pointer-events-none"
>
    {#each $toasts as toast (toast.id)}
        <div
            animate:flip={{ duration: 300 }}
            in:fly={{ x: 200, duration: 400 }}
            out:fade={{ duration: 200 }}
            class="pointer-events-auto win95-window min-w-[280px] max-w-[400px] flex flex-col p-0.5 shadow-retro-raised"
        >
            <!-- Title Bar -->
            <div
                class="win95-title-bar shrink-0 flex justify-between items-center py-0.5 px-2 {toast.type ===
                'error'
                    ? 'bg-red-800'
                    : toast.type === 'warning'
                      ? 'bg-yellow-700'
                      : 'bg-blue-800'}"
            >
                <div class="flex items-center gap-1">
                    <span
                        class="material-symbols-outlined text-[14px] text-white"
                    >
                        {toast.type === "error"
                            ? "error"
                            : toast.type === "warning"
                              ? "warning"
                              : "info"}
                    </span>
                    <span
                        class="text-[9px] font-bold uppercase tracking-tight text-white"
                    >
                        {toast.type === "error"
                            ? "System Error"
                            : "System Message"}
                    </span>
                </div>
                <button
                    onclick={() => toasts.remove(toast.id)}
                    class="w-3 h-3 bg-[#c0c0c0] text-black text-[10px] flex items-center justify-center border border-white border-b-black border-r-black leading-none font-bold active:bg-gray-400"
                    >x</button
                >
            </div>

            <!-- Content Area -->
            <div class="p-4 flex gap-4 items-start bg-[#d4d0c8]">
                <div class="shrink-0 pt-1">
                    {#if toast.type === "success"}
                        <span
                            class="material-symbols-outlined text-green-700 text-3xl"
                            >check_circle</span
                        >
                    {:else if toast.type === "error"}
                        <span
                            class="material-symbols-outlined text-red-700 text-3xl"
                            >dangerous</span
                        >
                    {:else if toast.type === "warning"}
                        <span
                            class="material-symbols-outlined text-yellow-700 text-3xl"
                            >warning</span
                        >
                    {:else}
                        <span
                            class="material-symbols-outlined text-blue-700 text-3xl"
                            >info</span
                        >
                    {/if}
                </div>
                <div class="flex-1 flex flex-col gap-3">
                    <p
                        class="text-[11px] font-bold text-black leading-snug font-mono whitespace-pre-wrap"
                    >
                        {toast.message}
                    </p>
                    <div class="flex justify-end">
                        <button
                            onclick={() => toasts.remove(toast.id)}
                            class="win95-btn px-6 py-1 text-[10px] font-bold uppercase bg-[#c0c0c0] text-black border-white"
                            >OK</button
                        >
                    </div>
                </div>
            </div>
        </div>
    {/each}
</div>
