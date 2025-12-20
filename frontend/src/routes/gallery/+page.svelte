<script lang="ts">
    import { onMount } from "svelte";
    import { toasts } from "$lib/stores/toasts";

    interface Image {
        id: string;
        run_id: string;
        file_path: string | null;
        overall_quality: number | null;
        anatomy_score: number | null;
        prompt_adherence: number | null;
        background_score: number | null;
        use_again: "yes" | "no" | "test_more" | null;
        is_rated: boolean;
    }

    let images = $state<Image[]>([]);
    let loading = $state(true);
    let total = $state(0);
    let offset = $state(0);
    const limit = 20;

    async function fetchUnratedImages() {
        try {
            loading = true;
            const res = await fetch(
                `http://localhost:8000/api/images?unrated_only=true&limit=${limit}&offset=${offset}`,
            );
            const data = await res.json();
            images = data.images;
            total = data.total;
        } catch (e) {
            console.error("Failed to fetch unrated images", e);
            toasts.error("Failed to load unrated images");
        } finally {
            loading = false;
        }
    }

    async function updateScore(imageId: string, payload: any) {
        try {
            const res = await fetch(
                `http://localhost:8000/api/images/${imageId}/score`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                },
            );
            const data = await res.json();
            if (res.ok) {
                // Update local state
                images = images.map((img) =>
                    img.id === imageId
                        ? { ...img, ...data.scores, is_rated: true }
                        : img,
                );
                // If it was the final rating (overall_quality set), we might want to hide it
                if (payload.overall_quality) {
                    setTimeout(() => {
                        images = images.filter((img) => img.id !== imageId);
                        total--;
                    }, 500);
                }
            } else {
                toasts.error("Failed to save score");
            }
        } catch (e: any) {
            toasts.error("Failed to save score: " + e.message);
        }
    }

    function getImageUrl(path: string | null) {
        if (!path) return "";
        const filename = path.split("/").pop();
        return `http://localhost:8000/images/${filename}`;
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
                class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-8"
            >
                {#each images as image (image.id)}
                    <div
                        class="win95-window flex flex-col bg-[#c0c0c0] p-1 group animate-in fade-in duration-300"
                    >
                        <div class="win95-title-bar !bg-blue-800 shrink-0 mb-1">
                            <span class="text-[9px]"
                                >IMG_{image.id.slice(0, 8)}.RAW</span
                            >
                            <a
                                href="/runs/{image.run_id}/review/{image.id}"
                                class="text-[9px] underline hover:text-yellow-300"
                                >VIEW_FULL</a
                            >
                        </div>

                        <div class="flex gap-2 p-1">
                            <!-- Image Left -->
                            <div
                                class="w-1/2 aspect-[512/768] win95-inset bg-black/10 overflow-hidden relative"
                            >
                                <img
                                    src={getImageUrl(image.file_path)}
                                    alt="Result"
                                    class="w-full h-full object-cover grayscale-[0.1] group-hover:grayscale-0"
                                />
                                {#if image.overall_quality}
                                    <div
                                        class="absolute top-1 right-1 size-8 flex items-center justify-center bg-win-magenta text-white font-pixel text-lg border-2 border-white shadow-[2px_2px_0_0_black]"
                                    >
                                        {image.overall_quality}
                                    </div>
                                {/if}
                            </div>

                            <!-- Controls Right -->
                            <div
                                class="w-1/2 flex flex-col gap-2 p-1 bg-[#d4d0c8] win95-inset overflow-y-auto scrollbar-hide"
                            >
                                <!-- Overall Quality 1-10 -->
                                <div class="flex flex-col gap-1 mb-2">
                                    <span
                                        class="text-[8px] font-bold uppercase text-win-purple"
                                        >Quality (1-10)</span
                                    >
                                    <div class="flex flex-wrap gap-1">
                                        {#each Array(10) as _, i}
                                            <button
                                                onclick={() =>
                                                    updateScore(image.id, {
                                                        overall_quality: i + 1,
                                                    })}
                                                class="size-5 flex items-center justify-center text-[9px] font-pixel border border-white {image.overall_quality ===
                                                i + 1
                                                    ? 'bg-win-magenta text-white'
                                                    : 'bg-[#c0c0c0] text-black hover:bg-white'}"
                                            >
                                                {i + 1}
                                            </button>
                                        {/each}
                                    </div>
                                </div>

                                <!-- Sliders -->
                                <div class="flex flex-col gap-2">
                                    <div class="flex flex-col gap-0.5">
                                        <div
                                            class="flex justify-between text-[8px] font-bold uppercase"
                                        >
                                            <span>Anatomy</span>
                                            <span class="text-blue-700"
                                                >{image.anatomy_score ||
                                                    "-"}</span
                                            >
                                        </div>
                                        <input
                                            type="range"
                                            min="1"
                                            max="10"
                                            step="1"
                                            value={image.anatomy_score || 5}
                                            onchange={(e) =>
                                                updateScore(image.id, {
                                                    anatomy_score: parseInt(
                                                        e.currentTarget.value,
                                                    ),
                                                })}
                                            class="range-retro-small"
                                        />
                                    </div>
                                    <div class="flex flex-col gap-0.5">
                                        <div
                                            class="flex justify-between text-[8px] font-bold uppercase"
                                        >
                                            <span>Prompt</span>
                                            <span class="text-win-purple"
                                                >{image.prompt_adherence ||
                                                    "-"}</span
                                            >
                                        </div>
                                        <input
                                            type="range"
                                            min="1"
                                            max="10"
                                            step="1"
                                            value={image.prompt_adherence || 5}
                                            onchange={(e) =>
                                                updateScore(image.id, {
                                                    prompt_adherence: parseInt(
                                                        e.currentTarget.value,
                                                    ),
                                                })}
                                            class="range-retro-small"
                                        />
                                    </div>
                                    <div class="flex flex-col gap-0.5">
                                        <div
                                            class="flex justify-between text-[8px] font-bold uppercase"
                                        >
                                            <span>Background</span>
                                            <span class="text-pink-600"
                                                >{image.background_score ||
                                                    "-"}</span
                                            >
                                        </div>
                                        <input
                                            type="range"
                                            min="1"
                                            max="10"
                                            step="1"
                                            value={image.background_score || 5}
                                            onchange={(e) =>
                                                updateScore(image.id, {
                                                    background_score: parseInt(
                                                        e.currentTarget.value,
                                                    ),
                                                })}
                                            class="range-retro-small"
                                        />
                                    </div>
                                </div>

                                <!-- Use Again -->
                                <div
                                    class="mt-auto pt-2 border-t border-gray-400"
                                >
                                    <div class="flex gap-1">
                                        <button
                                            onclick={() =>
                                                updateScore(image.id, {
                                                    use_again: "yes",
                                                })}
                                            class="flex-1 h-6 text-[8px] font-bold uppercase {image.use_again ===
                                            'yes'
                                                ? 'bg-green-600 text-white'
                                                : 'bg-white text-black'}"
                                            >YES</button
                                        >
                                        <button
                                            onclick={() =>
                                                updateScore(image.id, {
                                                    use_again: "test_more",
                                                })}
                                            class="flex-1 h-6 text-[8px] font-bold uppercase {image.use_again ===
                                            'test_more'
                                                ? 'bg-yellow-500 text-white'
                                                : 'bg-white text-black'}"
                                            >?</button
                                        >
                                        <button
                                            onclick={() =>
                                                updateScore(image.id, {
                                                    use_again: "no",
                                                })}
                                            class="flex-1 h-6 text-[8px] font-bold uppercase {image.use_again ===
                                            'no'
                                                ? 'bg-red-600 text-white'
                                                : 'bg-white text-black'}"
                                            >NO</button
                                        >
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>

<style>
    .range-retro-small {
        -webkit-appearance: none;
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
