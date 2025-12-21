<script lang="ts">
    import { onMount } from "svelte";
    import { toasts } from "$lib/stores/toasts";

    interface ImageCard {
        id: string;
        run_id: string;
        file_path: string | null;
        score_overall: number | null;
        is_failed: boolean;
        created_at?: string;
    }

    let images = $state<ImageCard[]>([]);
    let loading = $state(true);
    let total = $state(0);
    let offset = $state(0);
    const limit = 20;

    function normalizeImage(raw: any): ImageCard {
        const score =
            raw.score_overall ??
            raw.scores?.score_overall ??
            null;

        return {
            id: raw.id,
            run_id: raw.run_id,
            file_path: raw.file_path ?? null,
            score_overall: score,
            is_failed: raw.is_failed ?? false,
            created_at: raw.created_at,
        };
    }

    async function fetchUnratedImages() {
        try {
            loading = true;
            const res = await fetch(
                `http://localhost:8000/api/images?unrated_only=true&limit=${limit}&offset=${offset}`,
            );
            const data = await res.json();
            images = data.images.map(normalizeImage);
            total = data.total;
        } catch (e) {
            console.error("Failed to fetch unrated images", e);
            toasts.error("Failed to load unrated images");
        } finally {
            loading = false;
        }
    }

    function getImageUrl(path: string | null) {
        if (!path) return "";
        const filename = path.split("/").pop();
        return `http://localhost:8000/images/${filename}`;
    }

    function formatTimestamp(value?: string) {
        if (!value) return "";
        const date = new Date(value);
        return date.toLocaleDateString();
    }

    onMount(fetchUnratedImages);
</script>

<div class="flex flex-col h-full overflow-hidden font-mono bg-[#d4d0c8]">
    <!-- Window Header -->
    <div class="win95-title-bar shrink-0">
        <span class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[16px]"
                >photo_library</span
            >
            C:\SYSTEM\UNRATED_GALLERY.EXE
        </span>
        <div class="flex gap-1">
            <button
                class="win95-btn size-4 flex items-center justify-center text-[10px] p-0"
                >_</button
            >
            <button
                class="win95-btn size-4 flex items-center justify-center text-[10px] p-0"
                >□</button
            >
            <button
                class="win95-btn size-4 flex items-center justify-center text-[10px] p-0"
                >x</button
            >
        </div>
    </div>

    <!-- Toolbar -->
    <div
        class="p-4 border-b-2 border-white shadow-[0_1px_0_#808080] flex justify-between items-center bg-[#d4d0c8]"
    >
        <div>
            <h1
                class="text-2xl font-pixel uppercase tracking-wider text-black mt-1 leading-none"
            >
                Unrated Queue
            </h1>
            <p
                class="text-win-purple text-[10px] font-bold mt-1 tracking-tight italic"
            >
                &gt;_ {total} images waiting for evaluation vectors
            </p>
        </div>
        <div class="flex gap-2">
            <button
                onclick={() => {
                    offset = Math.max(0, offset - limit);
                    fetchUnratedImages();
                }}
                disabled={offset === 0}
                class="win95-btn px-4 h-8 text-[10px] font-bold uppercase disabled:opacity-50"
            >
                Prev
            </button>
            <button
                onclick={() => {
                    offset += limit;
                    fetchUnratedImages();
                }}
                disabled={offset + limit >= total}
                class="win95-btn px-4 h-8 text-[10px] font-bold uppercase disabled:opacity-50"
            >
                Next
            </button>
        </div>
    </div>

    <!-- Gallery Grid -->
    <div class="flex-1 overflow-y-auto p-6 bg-checkered custom-scrollbar">
        {#if loading && images.length === 0}
            <div class="flex justify-center py-20">
                <span class="loading loading-spinner loading-lg text-win-purple"
                ></span>
            </div>
        {:else if images.length === 0}
            <div
                class="win95-window p-10 bg-white max-w-xl mx-auto text-center mt-20 win95-inset"
            >
                <span
                    class="material-symbols-outlined text-6xl text-gray-300 mb-4"
                    >task_alt</span
                >
                <h2
                    class="text-xl font-bold uppercase font-pixel tracking-widest text-black"
                >
                    All Sector Clear
                </h2>
                <p class="text-xs text-gray-500 mt-2 italic">
                    All generated images have been successfully scored.
                </p>
            </div>
        {:else}
            <div
                class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-6"
            >
                {#each images as image (image.id)}
                    <a
                        href="/runs/{image.run_id}/review/{image.id}"
                        class="group flex flex-col gap-2 win95-window bg-[#c0c0c0] p-2 no-underline text-black"
                    >
                        <div class="flex items-center justify-between text-[9px] font-bold uppercase">
                            <span>IMG_{image.id.slice(0, 8)}.RAW</span>
                            <span class="text-gray-600">{formatTimestamp(image.created_at)}</span>
                        </div>
                        <div class="relative aspect-[3/4] win95-inset bg-black/10 overflow-hidden">
                            <img
                                src={getImageUrl(image.file_path)}
                                alt="Generated result"
                                class="w-full h-full object-cover grayscale-[0.15] group-hover:grayscale-0 transition-all duration-150"
                                loading="lazy"
                            />
                            {#if image.is_failed}
                                <div
                                    class="absolute inset-0 bg-red-900/40 flex items-center justify-center text-white font-bold text-xs"
                                >
                                    FAILED
                                </div>
                            {/if}
                            {#if typeof image.score_overall === "number"}
                                <div
                                    class="absolute -top-2 -right-2 w-8 h-8 flex items-center justify-center bg-blue-800 text-white font-pixel text-lg border-2 border-white shadow-[2px_2px_0_0_black]"
                                >
                                    {image.score_overall}
                                </div>
                            {/if}
                        </div>
                        <div class="flex justify-between text-[10px] uppercase">
                            <span class="text-gray-600">Run {image.run_id.slice(0, 6)}</span>
                            <span class="text-win-purple font-bold group-hover:text-black">Review →</span>
                        </div>
                    </a>
                {/each}
            </div>
        {/if}
    </div>
</div>

<style>
    .range-retro-small {
    -webkit-appearance: none;
    appearance: none;
        width: 100%;
        height: 4px;
        background: #f0f0f0;
        outline: none;
        border: 1px solid #808080;
    }

    .range-retro-small::-webkit-slider-thumb {
        -webkit-appearance: none;
        width: 10px;
        height: 10px;
        background: #c0c0c0;
        cursor: pointer;
        border: 1px solid white;
        border-right-color: #404040;
        border-bottom-color: #404040;
        box-shadow: 1px 1px 0 0 black;
    }

    /* Hide scrollbar but keep functionality */
    .scrollbar-hide::-webkit-scrollbar {
        display: none;
    }
    .scrollbar-hide {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }
</style>
