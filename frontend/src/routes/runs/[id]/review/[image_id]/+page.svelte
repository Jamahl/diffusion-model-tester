<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { page } from "$app/state";
    import { goto } from "$app/navigation";
    import { toasts } from "$lib/stores/toasts";

    interface Config {
        steps: number;
        scale: number;
        width: number;
        height: number;
        seed: number;
        scheduler: string;
        image_strength?: number;
        controlnet?: string;
        credit_cost: number;
    }

    interface ImageDetail {
        id: string;
        run_id: string;
        file_path: string | null;
        upscale_url: string | null;
        inf_id: string | null;
        scores: {
            overall_quality: number | null;
            anatomy_score: number | null;
            use_again: "yes" | "no" | "test_more" | null;
            prompt_adherence: number | null;
            background_score: number | null;
        };
        config: Config;
        run: {
            prompt: string;
            negative_prompt: string;
            model_id: string;
        };
    }

    let image = $state<ImageDetail | null>(null);
    let allImageIds = $state<string[]>([]);
    let currentIndex = $derived(allImageIds.indexOf(page.params.image_id));
    let loading = $state(true);
    let saving = $state(false);

    $effect(() => {
        if (page.params.image_id) {
            fetchDetail();
        }
    });

    // Upscale & Comparison State
    let upscaling = $state(false);
    let compareMode = $state(false);
    let upscaleType = $state<"esrgan" | "hires_fix">("esrgan");
    let upscaleScale = $state(2.0);
    let upscaleStrength = $state(0.6);

    async function fetchDetail() {
        if (!page.params.image_id || page.params.image_id === "undefined")
            return;
        try {
            const res = await fetch(
                `http://localhost:8000/api/images/${page.params.image_id}`,
            );
            if (!res.ok) throw new Error("Image not found");
            image = await res.json();
            if (!image?.upscale_url) compareMode = false;
        } catch (e) {
            console.error("Failed to fetch image detail", e);
        } finally {
            loading = false;
        }
    }

    async function handleUpscale() {
        if (!image || upscaling) return;
        upscaling = true;
        try {
            const res = await fetch(
                `http://localhost:8000/api/images/${image.id}/upscale`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        type: upscaleType,
                        scale: upscaleScale,
                        strength: upscaleStrength,
                    }),
                },
            );
            const data = await res.json();
            if (data.success) {
                toasts.success(`Image upscaled via ${upscaleType}`);
                await fetchDetail();
                compareMode = true;
            } else {
                toasts.error(data.detail || "Upscale failed");
            }
        } catch (e: any) {
            toasts.error("Upscale error: " + e.message);
        } finally {
            upscaling = false;
        }
    }

    async function fetchSiblingImages() {
        if (!page.params.id) return;
        try {
            const res = await fetch(
                `http://localhost:8000/api/images?run_id=${page.params.id}&limit=1000`,
            );
            const data = await res.json();
            if (data && data.images) {
                allImageIds = data.images.map((img: any) => img.id);
            }
        } catch (e) {
            console.error("Failed to fetch siblings", e);
        }
    }

    async function updateScore(payload: any) {
        if (!image || saving) return;
        saving = true;
        try {
            const res = await fetch(
                `http://localhost:8000/api/images/${image.id}/score`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                },
            );
            const data = await res.json();
            if (res.ok) {
                image.scores = { ...image.scores, ...data.scores };
            } else {
                toasts.error("Failed to save score");
            }
        } catch (e: any) {
            toasts.error("Failed to save score: " + e.message);
        } finally {
            saving = false;
        }
    }

    async function handleOverallQuality(score: number) {
        await updateScore({ overall_quality: score });
        navigateNext();
    }

    function navigateNext() {
        if (currentIndex < allImageIds.length - 1) {
            goto(
                `/runs/${page.params.id}/review/${allImageIds[currentIndex + 1]}`,
            );
        }
    }

    function navigatePrev() {
        if (currentIndex > 0) {
            goto(
                `/runs/${page.params.id}/review/${allImageIds[currentIndex - 1]}`,
            );
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (
            e.target instanceof HTMLTextAreaElement ||
            e.target instanceof HTMLInputElement
        )
            return;

        if (e.key === "ArrowRight") navigateNext();
        if (e.key === "ArrowLeft") navigatePrev();
        if (e.key === "Escape") goto(`/runs/${page.params.id}`);
        if (e.key === "c" || e.key === "C") {
            if (image?.upscale_url) compareMode = !compareMode;
        }

        if (e.key >= "1" && e.key <= "9") {
            handleOverallQuality(parseInt(e.key));
        } else if (e.key === "0") {
            handleOverallQuality(10);
        }
    }

    function getImageUrl(path: string | null) {
        if (!path) return "";
        if (path.startsWith("http")) return path;
        const filename = path.split("/").pop();
        return `http://localhost:8000/images/${filename}`;
    }

    onMount(() => {
        // fetchDetail handled by effect
        fetchSiblingImages();
        window.addEventListener("keydown", handleKeydown);
        window.focus();
    });

    onDestroy(() => {
        if (typeof window !== "undefined") {
            window.removeEventListener("keydown", handleKeydown);
        }
    });
</script>

<div class="flex h-full overflow-hidden font-mono bg-[#d4d0c8]">
    {#if loading}
        <div class="flex-1 flex items-center justify-center">
            <span class="loading loading-spinner loading-lg text-win-purple"
            ></span>
        </div>
    {:else if image}
        <!-- Left Side: Main View Window -->
        <div
            class="flex-1 flex flex-col h-full overflow-hidden border-r-2 border-white"
        >
            <div class="win95-title-bar shrink-0">
                <span class="flex items-center gap-2"
                    ><span class="material-symbols-outlined text-[16px]"
                        >visibility</span
                    >
                    IMAGE_REVIEW.EXE - {currentIndex + 1} OF {allImageIds.length}</span
                >
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

            <div
                class="flex-1 relative flex items-center justify-center p-8 bg-checkered min-h-0"
            >
                {#if compareMode && image.upscale_url}
                    <div class="grid grid-cols-2 gap-4 h-full w-full">
                        <div class="flex flex-col gap-2 h-full">
                            <div
                                class="flex justify-between items-center bg-blue-800 text-white px-2 py-0.5 text-[9px] font-bold uppercase border border-black shadow-[1px_1px_0_0_#000]"
                            >
                                <span>ORIGINAL_V0</span>
                                <span
                                    class="material-symbols-outlined text-[14px]"
                                    >photo_camera</span
                                >
                            </div>
                            <div
                                class="flex-1 win95-inset bg-black/10 flex items-center justify-center overflow-hidden"
                            >
                                <img
                                    src={getImageUrl(image.file_path)}
                                    alt="Original"
                                    class="max-w-full max-h-full object-contain shadow-retro-raised"
                                />
                            </div>
                        </div>
                        <div class="flex flex-col gap-2 h-full">
                            <div
                                class="flex justify-between items-center bg-win-magenta text-white px-2 py-0.5 text-[9px] font-bold uppercase border border-black shadow-[1px_1px_0_0_#000]"
                            >
                                <span>ENHANCED_V1</span>
                                <span
                                    class="material-symbols-outlined text-[14px]"
                                    >auto_fix_high</span
                                >
                            </div>
                            <div
                                class="flex-1 win95-inset bg-black/10 flex items-center justify-center overflow-hidden"
                            >
                                <img
                                    src={getImageUrl(image.upscale_url)}
                                    alt="Upscaled"
                                    class="max-w-full max-h-full object-contain shadow-retro-raised"
                                />
                            </div>
                        </div>
                    </div>
                {:else}
                    <div
                        class="relative group h-full w-full flex items-center justify-center"
                    >
                        <div class="relative win95-inset bg-black/5 p-1">
                            <img
                                src={getImageUrl(image.file_path)}
                                alt="Generation results"
                                class="max-w-full max-h-full object-contain shadow-retro-raised"
                            />
                            {#if image.upscale_url}
                                <div
                                    class="absolute bottom-2 right-2 bg-win-magenta text-white px-2 py-1 text-[10px] font-bold uppercase border border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] flex items-center gap-1"
                                >
                                    <span
                                        class="material-symbols-outlined text-[14px]"
                                        >check_circle</span
                                    > UPSCALE_AVAIL
                                </div>
                            {/if}
                        </div>
                    </div>
                {/if}

                <!-- Navigation Controls Overlaid -->
                <button
                    onclick={navigatePrev}
                    disabled={currentIndex === 0}
                    class="absolute left-4 btn-nav {currentIndex === 0
                        ? 'opacity-20 cursor-not-allowed'
                        : 'opacity-60 hover:opacity-100'}"
                >
                    <span class="material-symbols-outlined text-4xl text-black"
                        >chevron_left</span
                    >
                </button>
                <button
                    onclick={navigateNext}
                    disabled={currentIndex === allImageIds.length - 1}
                    class="absolute right-4 btn-nav {currentIndex ===
                    allImageIds.length - 1
                        ? 'opacity-20 cursor-not-allowed'
                        : 'opacity-60 hover:opacity-100'}"
                >
                    <span class="material-symbols-outlined text-4xl text-black"
                        >chevron_right</span
                    >
                </button>
            </div>

            <!-- Scoring Bar -->
            <div class="win95-window m-4 p-1 mt-0 shrink-0">
                <div class="flex items-center justify-between gap-4">
                    <div class="flex items-center gap-3 pl-2">
                        <span
                            class="text-[10px] font-bold uppercase mr-2 tracking-widest text-win-purple"
                            >Set Quality:</span
                        >
                        <div class="flex gap-1">
                            {#each Array(10) as _, i}
                                <button
                                    onclick={() => handleOverallQuality(i + 1)}
                                    class="w-8 h-8 flex items-center justify-center transition-none {image
                                        .scores.overall_quality ===
                                    i + 1
                                        ? 'win95-btn bg-win-magenta text-white border-white border-b-black border-r-black'
                                        : 'win95-btn bg-[#c0c0c0] text-black hover:bg-white active:bg-gray-400'}"
                                >
                                    <span class="font-pixel text-sm"
                                        >{i + 1}</span
                                    >
                                </button>
                            {/each}
                        </div>
                    </div>
                    <div class="flex gap-2 pr-2">
                        {#if image.upscale_url}
                            <button
                                onclick={() => (compareMode = !compareMode)}
                                class="win95-btn h-8 px-4 text-[10px] font-bold uppercase flex items-center gap-2 {compareMode
                                    ? 'bg-win-magenta text-white'
                                    : 'bg-white'}"
                            >
                                <span
                                    class="material-symbols-outlined text-[16px]"
                                    >{compareMode
                                        ? "visibility_off"
                                        : "compare"}</span
                                >
                                {compareMode ? "Exit Diff" : "Compare View"}
                            </button>
                        {/if}
                        <button
                            onclick={() =>
                                window.open(
                                    getImageUrl(
                                        image.upscale_url || image.file_path,
                                    ),
                                    "_blank",
                                )}
                            class="win95-btn h-8 px-4 text-[10px] font-bold uppercase flex items-center gap-2 bg-white"
                        >
                            <span class="material-symbols-outlined text-[16px]"
                                >open_in_new</span
                            > Full Screen
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Right Side: Meta Panel -->
        <div class="w-[360px] h-full flex flex-col shrink-0 bg-[#d4d0c8]">
            <div class="win95-title-bar shrink-0">
                <span>METADATA_INSPECTOR</span>
                <div class="flex gap-1">
                    <button
                        class="w-4 h-4 bg-[#c0c0c0] text-black text-[10px] flex items-center justify-center border border-white border-b-black border-r-black leading-none font-bold"
                    >
                        -
                    </button>
                    <button
                        class="w-4 h-4 bg-[#c0c0c0] text-black text-[10px] flex items-center justify-center border border-white border-b-black border-r-black leading-none font-bold"
                    >
                        x
                    </button>
                </div>
            </div>

            <div
                class="p-3 border-b border-white shadow-[0_1px_0_#808080] flex justify-between items-center bg-[#d4d0c8]"
            >
                <a
                    href="/runs/{page.params.id}"
                    class="win95-btn h-8 px-2 text-[10px] font-bold uppercase flex items-center gap-1 bg-white no-underline text-black"
                >
                    <span class="material-symbols-outlined text-[16px]"
                        >arrow_back</span
                    >
                    Back
                </a>
                <span class="text-[9px] font-bold opacity-40">INS_v1.0.4</span>
            </div>

            <div
                class="flex-1 overflow-y-auto p-4 flex flex-col gap-6 custom-scrollbar"
            >
                <!-- Score Summary -->
                <div class="win95-window p-1 bg-win-purple text-white">
                    <div class="p-4 flex flex-col items-center gap-2">
                        <span
                            class="text-[10px] uppercase font-bold tracking-widest opacity-80"
                            >Overall_Rating</span
                        >
                        <div class="font-pixel text-5xl">
                            {image.scores.overall_quality || "--"}
                        </div>
                        <span class="text-[9px] uppercase font-bold opacity-60"
                            >Calculated_Fidelity</span
                        >
                    </div>
                </div>
                <!-- Detailed Grading -->
                <div class="flex flex-col gap-1 p-1 win95-window">
                    <div
                        class="bg-blue-800 text-white px-2 py-0.5 text-[9px] font-bold uppercase flex justify-between items-center mb-2"
                    >
                        <span>DETAILED_GRADING</span>
                        <span class="material-symbols-outlined text-[14px]"
                            >fact_check</span
                        >
                    </div>
                    <div class="p-3 flex flex-col gap-5">
                        <div class="flex flex-col gap-1">
                            <div
                                class="flex justify-between items-center text-[10px] font-bold mb-1"
                            >
                                <span class="uppercase tracking-wider"
                                    >Anatomy Adherence</span
                                >
                                <span class="font-pixel text-blue-700 text-sm"
                                    >{image.scores.anatomy_score || "-"}</span
                                >
                            </div>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                step="1"
                                value={image.scores.anatomy_score || 5}
                                onchange={(e) =>
                                    updateScore({
                                        anatomy_score: parseInt(
                                            e.currentTarget.value,
                                        ),
                                    })}
                                class="range-retro"
                            />
                        </div>
                        <div class="flex flex-col gap-1">
                            <div
                                class="flex justify-between items-center text-[10px] font-bold mb-1"
                            >
                                <span class="uppercase tracking-wider"
                                    >Prompt Adherence</span
                                >
                                <span class="font-pixel text-win-purple text-sm"
                                    >{image.scores.prompt_adherence ||
                                        "-"}</span
                                >
                            </div>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                step="1"
                                value={image.scores.prompt_adherence || 5}
                                onchange={(e) =>
                                    updateScore({
                                        prompt_adherence: parseInt(
                                            e.currentTarget.value,
                                        ),
                                    })}
                                class="range-retro"
                            />
                        </div>
                        <div class="flex flex-col gap-1">
                            <div
                                class="flex justify-between items-center text-[10px] font-bold mb-1"
                            >
                                <span class="uppercase tracking-wider"
                                    >Background Fidelity</span
                                >
                                <span class="font-pixel text-pink-600 text-sm"
                                    >{image.scores.background_score ||
                                        "-"}</span
                                >
                            </div>
                            <input
                                type="range"
                                min="1"
                                max="10"
                                step="1"
                                value={image.scores.background_score || 5}
                                onchange={(e) =>
                                    updateScore({
                                        background_score: parseInt(
                                            e.currentTarget.value,
                                        ),
                                    })}
                                class="range-retro"
                            />
                        </div>

                        <div class="border-t border-gray-400 mt-2 pt-4">
                            <p
                                class="text-[10px] font-bold uppercase mb-3 text-center tracking-widest italic text-gray-600"
                            >
                                PRODUCTION_READY?
                            </p>
                            <div class="grid grid-cols-3 gap-2">
                                <button
                                    onclick={() =>
                                        updateScore({ use_again: "yes" })}
                                    class="win95-btn h-8 text-[9px] font-bold uppercase {image
                                        .scores.use_again === 'yes'
                                        ? 'bg-green-600 text-white'
                                        : 'bg-white'}">Yes</button
                                >
                                <button
                                    onclick={() =>
                                        updateScore({ use_again: "no" })}
                                    class="win95-btn h-8 text-[9px] font-bold uppercase {image
                                        .scores.use_again === 'no'
                                        ? 'bg-red-600 text-white'
                                        : 'bg-white'}">No</button
                                >
                                <button
                                    onclick={() =>
                                        updateScore({ use_again: "test_more" })}
                                    class="win95-btn h-8 text-[9px] font-bold uppercase {image
                                        .scores.use_again === 'test_more'
                                        ? 'bg-yellow-500 text-white'
                                        : 'bg-white'}">Maybe</button
                                >
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Enhance Section -->
                <div class="win95-window p-1">
                    <div
                        class="bg-teal-700 text-white px-2 py-0.5 text-[9px] font-bold uppercase flex justify-between items-center mb-2"
                    >
                        <span>UPSCALER_ENGINE.DLL</span>
                        <span class="material-symbols-outlined text-[14px]"
                            >auto_fix_high</span
                        >
                    </div>
                    <div class="p-3 flex flex-col gap-4">
                        <div
                            class="flex border-2 border-[#808080] border-b-white border-r-white bg-white p-[1px]"
                        >
                            <button
                                onclick={() => (upscaleType = "esrgan")}
                                class="flex-1 h-7 text-[9px] font-bold uppercase transition-none {upscaleType ===
                                'esrgan'
                                    ? 'bg-win-purple text-white'
                                    : 'bg-white text-black hover:bg-gray-100'}"
                                >ESRGAN</button
                            >
                            <button
                                onclick={() => (upscaleType = "hires_fix")}
                                class="flex-1 h-7 text-[9px] font-bold uppercase transition-none {upscaleType ===
                                'hires_fix'
                                    ? 'bg-win-purple text-white'
                                    : 'bg-white text-black hover:bg-gray-100'}"
                                >Hires Fix</button
                            >
                        </div>
                        {#if upscaleType === "esrgan"}
                            <div class="flex flex-col gap-1">
                                <span class="text-[10px] font-bold uppercase"
                                    >Mult: {upscaleScale}x</span
                                >
                                <input
                                    type="range"
                                    min="2"
                                    max="4"
                                    step="0.5"
                                    bind:value={upscaleScale}
                                    class="range-retro"
                                />
                            </div>
                        {:else}
                            <div class="flex flex-col gap-1">
                                <span class="text-[10px] font-bold uppercase"
                                    >Str: {upscaleStrength}</span
                                >
                                <input
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.1"
                                    bind:value={upscaleStrength}
                                    class="range-retro"
                                />
                            </div>
                        {/if}
                        <button
                            onclick={handleUpscale}
                            disabled={upscaling}
                            class="win95-btn w-full h-10 bg-win-magenta text-white font-bold uppercase text-xs flex items-center justify-center gap-2"
                        >
                            {#if upscaling}
                                <span class="loading loading-spinner h-4 w-4"
                                ></span> WORKING...
                            {:else}
                                <span
                                    class="material-symbols-outlined text-[20px]"
                                    >bolt</span
                                > Initiate Upscale
                            {/if}
                        </button>
                    </div>
                </div>

                <!-- Param Stack -->
                <div class="win95-window p-1">
                    <div
                        class="bg-gray-700 text-white px-2 py-0.5 text-[9px] font-bold uppercase flex justify-between items-center mb-2"
                    >
                        <span>CONFIG_STACK</span>
                        <span class="material-symbols-outlined text-[14px]"
                            >settings</span
                        >
                    </div>
                    <div class="p-3 flex flex-col gap-2">
                        <div class="grid grid-cols-2 gap-2 text-[10px]">
                            <div
                                class="win95-inset bg-gray-50 px-2 py-1 flex justify-between"
                            >
                                <span class="opacity-60 uppercase font-bold"
                                    >Steps</span
                                >
                                <span class="font-bold"
                                    >{image.config.steps}</span
                                >
                            </div>
                            <div
                                class="win95-inset bg-gray-50 px-2 py-1 flex justify-between"
                            >
                                <span class="opacity-60 uppercase font-bold"
                                    >CFG</span
                                >
                                <span class="font-bold"
                                    >{image.config.scale}</span
                                >
                            </div>
                            <div
                                class="win95-inset bg-gray-50 px-2 py-1 flex justify-between"
                            >
                                <span class="opacity-60 uppercase font-bold"
                                    >W</span
                                >
                                <span class="font-bold"
                                    >{image.config.width}px</span
                                >
                            </div>
                            <div
                                class="win95-inset bg-gray-50 px-2 py-1 flex justify-between"
                            >
                                <span class="opacity-60 uppercase font-bold"
                                    >H</span
                                >
                                <span class="font-bold"
                                    >{image.config.height}px</span
                                >
                            </div>
                        </div>
                        <div
                            class="win95-inset bg-gray-50 px-2 py-2 flex flex-col gap-1 overflow-hidden"
                        >
                            <span
                                class="text-[9px] uppercase font-bold opacity-40"
                                >Scheduler_Engine</span
                            >
                            <span
                                class="text-[10px] font-bold uppercase truncate italic"
                                >{image.config.scheduler}</span
                            >
                        </div>
                        <div
                            class="win95-inset bg-gray-50 px-2 py-2 flex flex-col gap-1 overflow-hidden"
                        >
                            <span
                                class="text-[9px] uppercase font-bold opacity-40"
                                >Seed_ID</span
                            >
                            <span
                                class="text-[10px] font-bold truncate font-mono"
                                >{image.config.seed}</span
                            >
                        </div>
                    </div>
                </div>

                <!-- Prompt Inset -->
                <div class="win95-window p-1">
                    <div
                        class="bg-gray-700 text-white px-2 py-0.5 text-[9px] font-bold uppercase flex justify-between items-center mb-2"
                    >
                        <span>PROMPT_BUFFER</span>
                        <span class="material-symbols-outlined text-[14px]"
                            >short_text</span
                        >
                    </div>
                    <div
                        class="p-3 bg-white win95-inset font-mono text-[10px] leading-relaxed max-h-[150px] overflow-y-auto custom-scrollbar italic whitespace-pre-wrap text-gray-700"
                    >
                        "{image.run.prompt}"
                    </div>
                </div>

                <!-- Footer Navigation -->
                <div class="flex flex-col gap-2 mt-auto pb-4">
                    <a
                        href="/runs/{image.run_id}"
                        class="win95-btn h-10 w-full flex items-center justify-center gap-2 bg-white text-black font-bold uppercase text-xs no-underline"
                    >
                        <span class="material-symbols-outlined text-[20px]"
                            >grid_view</span
                        > Return to Gallery
                    </a>
                </div>
            </div>

            <!-- Terminal Keyboard Help -->
            <div class="p-2 bg-[#d4d0c8] border-t-2 border-white">
                <div
                    class="flex items-center justify-between bg-black px-2 py-1 mb-1"
                >
                    <span class="text-[9px] text-white font-bold"
                        >HOTKEYS.SYS</span
                    >
                    <span
                        class="material-symbols-outlined text-green-400 text-[14px]"
                        >keyboard</span
                    >
                </div>
                <div
                    class="bg-black p-3 font-mono text-[9px] text-green-500 leading-tight border-2 border-black win95-inset"
                >
                    <div class="grid grid-cols-2 gap-y-2">
                        <span>[ARROW_LEFT/RIGHT]</span>
                        <span class="text-white">NAVIGATE</span>
                        <span>[KEYS_1-0]</span>
                        <span class="text-white">SET_QUALITY</span>
                        <span>[KEY_C]</span>
                        <span class="text-white">TOGGLE_COMPARE</span>
                    </div>
                    <p class="mt-3 opacity-40 italic">// AUTO_SAVE: ON</p>
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    .btn-nav {
        @apply transition-transform active:scale-90 flex items-center justify-center p-2 rounded-full bg-white/40 border-2 border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)];
    }

    .range-retro {
        -webkit-appearance: none;
        width: 100%;
        height: 6px;
        background: #f0f0f0;
        outline: none;
        border: 2px solid #808080;
        border-right-color: white;
        border-bottom-color: white;
    }

    .range-retro::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 16px;
        height: 16px;
        background: #c0c0c0;
        cursor: pointer;
        border: 2px solid white;
        border-right-color: #404040;
        border-bottom-color: #404040;
        box-shadow: 1px 1px 0 0 black;
    }
</style>
