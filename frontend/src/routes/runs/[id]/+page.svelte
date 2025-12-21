<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/state";
    import { toasts } from "$lib/stores/toasts";

    interface Run {
        id: string;
        batch_number: number;
        name: string;
        prompt: string;
        model_id: string;
        counts: {
            total_images: number;
            unrated: number;
            upscaled: number;
        };
        config?: {
            steps: number;
            scale: number;
            width: number;
            height: number;
            seed: number;
            scheduler: string;
        };
    }

    interface ImageScores {
        facial_detail_realism?: number | null;
        body_proportions?: number | null;
        complexity_artistry?: number | null;
        composition_framing?: number | null;
        lighting_color?: number | null;
        resolution_clarity?: number | null;
        style_consistency?: number | null;
        prompt_adherence?: number | null;
        artifacts?: number | null;
    }

    interface Image {
        id: string;
        file_path: string | null;
        score_overall: number | null;
        is_rated: boolean;
        is_failed: boolean;
        upscale_url: string | null;
        scores?: ImageScores;
        flaws?: string;
        curation_status?: string;
    }

    let run = $state<Run | null>(null);
    let images = $state<Image[]>([]);
    let unratedOnly = $state(false);
    let loading = $state(true);
    let error = $state<string | null>(null);
    async function fetchRunDetail() {
        const runId = page.params.id;
        if (!runId) return;
        try {
            const res = await fetch(
                `http://localhost:8000/api/runs/${runId}`,
            );
            if (!res.ok) throw new Error("Run not found");
            const data = await res.json();

            // Get config from first image if available
            let config = null;
            if (data.counts.total_images > 0) {
                const imgRes = await fetch(
                    `http://localhost:8000/api/images?run_id=${runId}&limit=1`,
                );
                const imgData = await imgRes.json();
                if (imgData.images.length > 0) {
                    config = imgData.images[0].config;
                }
            }

            run = { ...data, config };
        } catch (e: any) {
            error = e.message;
        }
    }

    async function fetchImages() {
        const runId = page.params.id;
        if (!runId) return;
        try {
            loading = true;
            const url = new URL(`http://localhost:8000/api/images`);
            url.searchParams.set("run_id", runId);
            if (unratedOnly) url.searchParams.set("unrated_only", "true");

            const res = await fetch(url.toString());
            const data = await res.json();
            images = data.images;
        } catch (e: any) {
            console.error("Failed to fetch images", e);
        } finally {
            loading = false;
        }
    }

    async function toggleFailed(imageId: string, currentStatus: boolean) {
        try {
            const res = await fetch(
                `http://localhost:8000/api/images/${imageId}/score`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ is_failed: !currentStatus }),
                },
            );

            if (res.ok) {
                // Update local state
                images = images.map((img) =>
                    img.id === imageId
                        ? { ...img, is_failed: !currentStatus }
                        : img,
                );
                toasts.success(
                    `Image marked as ${!currentStatus ? "failed" : "restored"}`,
                );
            }
        } catch (e) {
            toasts.error("Failed to update status");
        }
    }

    function getImageUrl(path: string | null) {
        if (!path) return "";
        const filename = path.split("/").pop();
        return `http://localhost:8000/images/${filename}`;
    }

    $effect(() => {
        fetchImages();
    });

    onMount(async () => {
        await fetchRunDetail();
        await fetchImages();
    });
</script>

<div class="flex flex-col h-full overflow-hidden font-mono bg-[#d4d0c8]">
    <!-- Window Header -->
    <div class="win95-title-bar shrink-0">
        <span class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[16px]"
                >folder_open</span
            >
            C:\EXPERIMENTS\BATCH_{run?.batch_number || "..."}.DIR
        </span>
        <div class="flex gap-1">
            <button
                class="w-4 h-4 bg-[#c0c0c0] text-black text-[10px] flex items-center justify-center border border-white border-b-black border-r-black leading-none font-bold"
                >_</button
            >
            <button
                class="w-4 h-4 bg-[#c0c0c0] text-black text-[10px] flex items-center justify-center border border-white border-b-black border-r-black leading-none font-bold"
                >□</button
            >
            <button
                class="w-4 h-4 bg-[#c0c0c0] text-black text-[10px] flex items-center justify-center border border-white border-b-black border-r-black leading-none font-bold"
                >x</button
            >
        </div>
    </div>

    <!-- Toolbar -->
    <div
        class="p-4 border-b-2 border-white shadow-[0_1px_0_#808080] flex flex-col md:flex-row justify-between items-end gap-4"
    >
        {#if run}
            <div class="flex flex-col gap-1">
                <div class="flex items-center gap-3">
                    <span
                        class="bg-blue-800 text-white px-2 py-0.5 text-[10px] font-bold uppercase border border-black shadow-[1px_1px_0_0_#000]"
                        >RUN_ID: {run.batch_number}</span
                    >
                    <h1
                        class="text-2xl font-pixel uppercase tracking-wider text-black leading-none"
                    >
                        {run.name || "Untitled Generation"}
                    </h1>
                </div>
                <p
                    class="text-win-purple text-[10px] font-bold mt-1 tracking-tight italic max-w-2xl line-clamp-1"
                >
                    &gt;_ Prompt: {run.prompt}
                </p>
                <div
                    class="flex gap-4 mt-1 text-[9px] uppercase font-bold text-gray-600"
                >
                    <span>Engine: {run.model_id}</span>
                    <span class="text-blue-700"
                        >Total: {run.counts.total_images}</span
                    >
                    <span class="text-win-magenta"
                        >Unrated: {run.counts.unrated}</span
                    >
                </div>
                {#if run.config}
                    <div
                        class="mt-2 text-[9px] font-mono text-gray-500 flex flex-wrap gap-x-4 gap-y-1 bg-white/50 p-1 border border-white win95-inset w-full"
                    >
                        <span>STEPS: {run.config.steps}</span>
                        <span>CFG: {run.config.scale}</span>
                        <span>DIM: {run.config.width}x{run.config.height}</span>
                        <span>SCHEDULER: {run.config.scheduler}</span>
                        <span>SEED: {run.config.seed}</span>
                    </div>
                {/if}
            </div>
        {/if}

        <div class="flex gap-3">
            <div
                class="win95-btn bg-white px-3 flex items-center gap-4 h-10 border-2 border-white border-b-black border-r-black"
            >
                <span class="text-[10px] font-bold uppercase text-black"
                    >Filter: Unrated</span
                >
                <input
                    type="checkbox"
                    bind:checked={unratedOnly}
                    class="w-4 h-4 accent-win-magenta cursor-pointer"
                />
            </div>
            <a
                href="/"
                class="win95-btn h-10 px-4 text-xs font-bold uppercase flex items-center gap-2 bg-white no-underline text-black"
            >
                <span class="material-symbols-outlined text-[18px]"
                    >arrow_back</span
                > Dashboard
            </a>
        </div>
    </div>

    <!-- Gallery Area -->
    <div class="flex-1 overflow-y-auto p-6 bg-checkered custom-scrollbar">
        {#if error}
            <div
                class="win95-window p-4 bg-red-100 text-red-800 border-2 border-red-800 max-w-md mx-auto mt-20"
            >
                <p class="font-bold flex items-center gap-2">
                    <span class="material-symbols-outlined">error</span> CRITICAL
                    SYSTEM ERROR
                </p>
                <p class="text-xs mt-2">{error}</p>
            </div>
        {:else if loading && images.length === 0}
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
                    >folder_off</span
                >
                <h2
                    class="text-xl font-bold uppercase font-pixel tracking-widest text-black"
                >
                    Directory is Empty
                </h2>
                <p class="text-xs text-gray-500 mt-2 italic">
                    {unratedOnly
                        ? "No unrated image-sectors found in this partition."
                        : "No generation data clusters detected."}
                </p>
            </div>
        {:else}
            <div
                class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8 gap-6 max-w-[1800px] mx-auto"
            >
                {#each images as image}
                    <div class="flex flex-col gap-2 group">
                        <div
                            class="relative aspect-[3/4] win95-window p-1 bg-[#c0c0c0] group-hover:bg-win-magenta transition-colors duration-0"
                        >
                            <!-- Failed Toggle Button -->
                            <button
                                onclick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    toggleFailed(image.id, image.is_failed);
                                }}
                                class="absolute top-2 left-2 z-20 w-5 h-5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity {image.is_failed
                                    ? 'bg-red-600 text-white opacity-100'
                                    : 'bg-[#c0c0c0] text-black hover:bg-red-200'} border border-white shadow-[1px_1px_0_0_black]"
                                title={image.is_failed
                                    ? "Mark valid"
                                    : "Mark failed"}
                            >
                                <span
                                    class="material-symbols-outlined text-[14px]"
                                >
                                    {image.is_failed ? "close" : "block"}
                                </span>
                            </button>

                            <a
                                href="/runs/{run?.id}/review/{image.id}"
                                class="w-full h-full win95-inset bg-black/5 overflow-hidden block"
                            >
                                <img
                                    src={getImageUrl(image.file_path)}
                                    alt="Generated result"
                                    class="w-full h-full object-cover grayscale-[0.2] group-hover:grayscale-0 transition-all duration-0"
                                    loading="lazy"
                                />

                                {#if image.is_failed}
                                    <div
                                        class="absolute inset-0 bg-red-900/50 flex items-center justify-center z-10 pointer-events-none backdrop-grayscale"
                                    >
                                        <span
                                            class="font-bold text-white text-xs bg-red-600 px-2 py-1 transform -rotate-12 border border-white"
                                            >FAILED</span
                                        >
                                    </div>
                                {/if}

                                {#if typeof image.score_overall === "number"}
                                    <div
                                        class="absolute -top-2 -right-2 w-8 h-8 flex items-center justify-center bg-blue-800 text-white font-pixel text-lg border-2 border-white shadow-[2px_2px_0_0_black] z-10"
                                    >
                                        {image.score_overall}
                                    </div>
                                {/if}

                                {#if image.upscale_url}
                                    <div
                                        class="absolute top-8 -right-2 px-1 bg-yellow-400 text-black font-bold text-[8px] border-2 border-white shadow-[2px_2px_0_0_black] z-10 uppercase tracking-tighter"
                                    >
                                        UPSCALED
                                    </div>
                                {/if}

                                {#if scoringId === image.id}
                                    <div
                                        class="absolute inset-0 bg-black/40 flex items-center justify-center z-30"
                                    >
                                        <span
                                            class="loading loading-spinner loading-md text-white"
                                        ></span>
                                    </div>
                                {/if}
                            </a>
                        </div>
                        <div class="flex flex-col items-center">
                            <span
                                class="text-[9px] font-bold text-center uppercase tracking-tighter truncate w-full group-hover:bg-blue-800 group-hover:text-white px-1"
                                >Img_{image.id.slice(0, 8)}.raw</span
                            >
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>

    <!-- Status Bar -->
    <div
        class="h-6 bg-[#c0c0c0] border-t-2 border-white flex items-center px-2 gap-4 shrink-0 text-[10px] uppercase font-bold text-gray-700"
    >
        <div
            class="flex items-center gap-1 border-r border-[#808080] pr-4 h-full"
        >
            <span class="material-symbols-outlined text-[14px]">storage</span>
            <span>{images.length} Object(s)</span>
        </div>
        <div class="flex items-center gap-1">
            <span class="material-symbols-outlined text-[14px]"
                >check_circle</span
            >
            <span>System: READY</span>
        </div>
        <div class="ml-auto flex items-center gap-2">
            <span>TIP: HOVER TO QUICK-SCORE</span>
        </div>
    </div>
</div>
