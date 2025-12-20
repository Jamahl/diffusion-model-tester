<script lang="ts">
    import { onMount } from "svelte";
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

    // Upscale & Comparison State
    let upscaling = $state(false);
    let compareMode = $state(false);
    let upscaleType = $state<"esrgan" | "hires_fix">("esrgan");
    let upscaleScale = $state(2.0);
    let upscaleStrength = $state(0.6);

    async function fetchDetail() {
        try {
            const res = await fetch(
                `http://localhost:8000/api/images/${page.params.image_id}`,
            );
            image = await res.json();
            // Reset comparison if image changes and has no upscale
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
                // Refresh to get updated upscale_url
                await fetchDetail();
                compareMode = true; // Auto-show comparison
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
        try {
            const res = await fetch(
                `http://localhost:8000/api/images?run_id=${page.params.id}&limit=1000`,
            );
            const data = await res.json();
            allImageIds = data.images.map((img: any) => img.id);
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
        if (e.key === "c" || e.key === "C") {
            if (image?.upscale_url) compareMode = !compareMode;
        }

        // 1-9 keys, and 0 for 10
        if (e.key >= "1" && e.key <= "9") {
            handleOverallQuality(parseInt(e.key));
        } else if (e.key === "0") {
            handleOverallQuality(10);
        }
    }

    function getImageUrl(path: string | null) {
        if (!path) return "";
        if (path.startsWith("http")) return path; // Already a URL (upscale_url)
        const filename = path.split("/").pop();
        return `http://localhost:8000/images/${filename}`;
    }

    onMount(() => {
        fetchDetail();
        fetchSiblingImages();
        window.addEventListener("keydown", handleKeydown);
        return () => window.removeEventListener("keydown", handleKeydown);
    });
</script>

<div class="h-[calc(100vh-120px)] flex flex-col md:flex-row gap-6">
    {#if loading}
        <div class="flex-1 flex items-center justify-center">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else if image}
        <!-- Left Side: Main View -->
        <div
            class="flex-1 flex flex-col bg-base-300 rounded-2xl overflow-hidden relative group"
        >
            <div class="flex-1 flex items-center justify-center p-4 min-h-0">
                {#if compareMode && image.upscale_url}
                    <div class="grid grid-cols-2 gap-2 h-full w-full">
                        <div class="relative flex flex-col gap-2 h-full">
                            <span class="absolute top-2 left-2 badge badge-neutral bg-black/50 border-none z-10 uppercase text-[10px] font-bold">Original</span>
                            <div class="flex-1 flex items-center justify-center bg-black/20 rounded-lg overflow-hidden">
                                <img
                                    src={getImageUrl(image.file_path)}
                                    alt="Original"
                                    class="max-w-full max-h-full object-contain"
                                />
                            </div>
                        </div>
                        <div class="relative flex flex-col gap-2 h-full">
                            <span class="absolute top-2 left-2 badge badge-secondary z-10 uppercase text-[10px] font-bold">Upscaled ✨</span>
                            <div class="flex-1 flex items-center justify-center bg-black/20 rounded-lg overflow-hidden">
                                <img
                                    src={getImageUrl(image.upscale_url)}
                                    alt="Upscaled"
                                    class="max-w-full max-h-full object-contain"
                                />
                            </div>
                        </div>
                    </div>
                {:else}
                    <img
                        src={getImageUrl(image.file_path)}
                        alt="Generation results"
                        class="max-w-full max-h-full object-contain shadow-2xl rounded-lg"
                    />
                {/if}
            </div>

            <!-- Navigation Overlays -->
            <button
                onclick={navigatePrev}
                class="absolute left-4 top-1/2 -translate-y-1/2 btn btn-circle btn-ghost opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 z-20"
                disabled={currentIndex === 0}
            >
                ❮
            </button>
            <button
                onclick={navigateNext}
                class="absolute right-4 top-1/2 -translate-y-1/2 btn btn-circle btn-ghost opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 z-20"
                disabled={currentIndex === allImageIds.length - 1}
            >
                ❯
            </button>

            <div
                class="p-4 bg-base-200/50 backdrop-blur-sm border-t border-white/10 flex items-center justify-between z-20"
            >
                <div class="flex items-center gap-4">
                    <div class="text-xs opacity-50 font-mono">
                        {currentIndex + 1} / {allImageIds.length}
                    </div>
                    {#if image.upscale_url}
                        <button 
                            onclick={() => compareMode = !compareMode}
                            class="btn btn-xs {compareMode ? 'btn-secondary' : 'btn-outline opacity-70'}"
                        >
                            {compareMode ? 'Exit Comparison' : 'Compare Before/After'}
                        </button>
                    {/if}
                </div>
                <div class="flex gap-1">
                    {#each Array(10) as _, i}
                        <button
                            onclick={() => handleOverallQuality(i + 1)}
                            class="btn btn-square btn-sm {image.scores
                                .overall_quality ===
                            i + 1
                                ? 'btn-primary'
                                : 'btn-ghost opacity-60'}"
                        >
                            {i + 1}
                        </button>
                    {/each}
                </div>
            </div>
        </div>

        <!-- Right Side: Meta Panel -->
        <div class="w-full md:w-80 flex flex-col gap-6 overflow-y-auto">
            <!-- Detailed Review Card -->
            <div class="card bg-base-200 shadow-xl border border-white/5 shrink-0">
                <div class="card-body p-4 flex flex-col gap-4">
                    <h3 class="text-xs font-bold uppercase tracking-widest opacity-40">Detailed Review</h3>
                    
                    <div class="flex flex-col gap-4">
                        <!-- Anatomy Score -->
                        <div class="form-control">
                            <label class="label p-0 pb-1">
                                <span class="label-text text-[11px] font-semibold opacity-70">Anatomy</span>
                                <span class="label-text-alt badge badge-sm">{image.scores.anatomy_score || '-'}</span>
                            </label>
                            <input 
                                type="range" min="1" max="10" step="1" 
                                value={image.scores.anatomy_score || 5} 
                                onchange={(e) => updateScore({ anatomy_score: parseInt(e.currentTarget.value) })}
                                class="range range-xs range-primary" 
                            />
                        </div>

                        <!-- Prompt Adherence -->
                        <div class="form-control">
                            <label class="label p-0 pb-1">
                                <span class="label-text text-[11px] font-semibold opacity-70">Prompt Adherence</span>
                                <span class="label-text-alt badge badge-sm">{image.scores.prompt_adherence || '-'}</span>
                            </label>
                            <input 
                                type="range" min="1" max="10" step="1" 
                                value={image.scores.prompt_adherence || 5} 
                                onchange={(e) => updateScore({ prompt_adherence: parseInt(e.currentTarget.value) })}
                                class="range range-xs range-secondary" 
                            />
                        </div>

                        <!-- Background Score -->
                        <div class="form-control">
                            <label class="label p-0 pb-1">
                                <span class="label-text text-[11px] font-semibold opacity-70">Background</span>
                                <span class="label-text-alt badge badge-sm">{image.scores.background_score || '-'}</span>
                            </label>
                            <input 
                                type="range" min="1" max="10" step="1" 
                                value={image.scores.background_score || 5} 
                                onchange={(e) => updateScore({ background_score: parseInt(e.currentTarget.value) })}
                                class="range range-xs range-accent" 
                            />
                        </div>

                        <div class="divider my-0 opacity-10"></div>

                        <!-- Use Again -->
                        <div class="form-control">
                            <label class="label p-0 pb-2">
                                <span class="label-text text-[10px] uppercase font-bold opacity-40">Production Quality?</span>
                            </label>
                            <div class="grid grid-cols-3 gap-1">
                                <button 
                                    class="btn btn-xs {image.scores.use_again === 'yes' ? 'btn-success' : 'btn-ghost bg-base-300'}"
                                    onclick={() => updateScore({ use_again: 'yes' })}
                                >Yes</button>
                                <button 
                                    class="btn btn-xs {image.scores.use_again === 'no' ? 'btn-error' : 'btn-ghost bg-base-300'}"
                                    onclick={() => updateScore({ use_again: 'no' })}
                                >No</button>
                                <button 
                                    class="btn btn-xs {image.scores.use_again === 'test_more' ? 'btn-warning' : 'btn-ghost bg-base-300'}"
                                    onclick={() => updateScore({ use_again: 'test_more' })}
                                >Maybe</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card bg-base-200 shadow-xl overflow-y-auto max-h-full border border-white/5">
                    <!-- Enhance Section -->
                    <div class="bg-base-300/50 rounded-xl p-4 border border-white/5">
                        <h3 class="text-[10px] font-bold uppercase tracking-widest opacity-40 mb-3 flex items-center justify-between">
                            Enhance Image
                            {#if image.upscale_url}
                                <span class="badge badge-secondary badge-xs">Done</span>
                            {/if}
                        </h3>
                        
                        <div class="flex flex-col gap-3">
                            <div class="join w-full">
                                <button 
                                    class="join-item btn btn-xs flex-1 {upscaleType === 'esrgan' ? 'btn-primary' : 'btn-ghost'}"
                                    onclick={() => upscaleType = 'esrgan'}
                                >ESRGAN</button>
                                <button 
                                    class="join-item btn btn-xs flex-1 {upscaleType === 'hires_fix' ? 'btn-primary' : 'btn-ghost'}"
                                    onclick={() => upscaleType = 'hires_fix'}
                                >Hires Fix</button>
                            </div>

                            {#if upscaleType === 'esrgan'}
                                <div class="form-control">
                                    <label class="label p-0 py-1">
                                        <span class="label-text text-[10px]">Scale: {upscaleScale}x</span>
                                    </label>
                                    <input type="range" min="2" max="4" step="0.5" bind:value={upscaleScale} class="range range-xs range-primary" />
                                </div>
                            {:else}
                                <div class="form-control">
                                    <label class="label p-0 py-1">
                                        <span class="label-text text-[10px]">Strength: {upscaleStrength}</span>
                                    </label>
                                    <input type="range" min="0" max="1" step="0.1" bind:value={upscaleStrength} class="range range-xs range-primary" />
                                </div>
                            {/if}

                            <button 
                                class="btn btn-secondary btn-sm w-full mt-1" 
                                onclick={handleUpscale}
                                disabled={upscaling}
                            >
                                {#if upscaling}
                                    <span class="loading loading-spinner loading-xs"></span>
                                {:else}
                                    ✨ Upscale Image
                                {/if}
                            </button>
                        </div>
                    </div>

                    <div class="divider my-0 opacity-20"></div>

                    <div class="mb-2">
                        <h3
                            class="text-xs font-bold uppercase tracking-widest opacity-40 mb-3"
                        >
                            Parameters
                        </h3>
                        <div class="grid grid-cols-2 gap-y-3 text-sm">
                            <span class="opacity-60 flex items-center gap-1">
                                Steps
                                <div
                                    class="tooltip tooltip-right"
                                    data-tip="The number of denoising steps used for this generation."
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        class="w-3 h-3 stroke-current opacity-50"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path></svg
                                    >
                                </div>
                            </span>
                            <span class="font-mono text-right"
                                >{image.config.steps}</span
                            >

                            <span class="opacity-60 flex items-center gap-1">
                                CFG Scale
                                <div
                                    class="tooltip tooltip-right"
                                    data-tip="Guidance scale determining how closely the model followed the prompt."
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        class="w-3 h-3 stroke-current opacity-50"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path></svg
                                    >
                                </div>
                            </span>
                            <span class="font-mono text-right"
                                >{image.config.scale}</span
                            >

                            <span class="opacity-60">Width</span>
                            <span class="font-mono text-right"
                                >{image.config.width}px</span
                            >

                            <span class="opacity-60">Height</span>
                            <span class="font-mono text-right"
                                >{image.config.height}px</span
                            >

                            <span class="opacity-60 flex items-center gap-1">
                                Scheduler
                                <div
                                    class="tooltip tooltip-right"
                                    data-tip="The sampling algorithm used for this image."
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        class="w-3 h-3 stroke-current opacity-50"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path></svg
                                    >
                                </div>
                            </span>
                            <span
                                class="font-mono text-right text-[10px] uppercase truncate ml-2"
                                >{image.config.scheduler}</span
                            >

                            <span class="opacity-60 flex items-center gap-1">
                                Seed
                                <div
                                    class="tooltip tooltip-right"
                                    data-tip="The unique starting seed for this generation."
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        class="w-3 h-3 stroke-current opacity-50"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path></svg
                                    >
                                </div>
                            </span>
                            <span class="font-mono text-right truncate ml-2"
                                >{image.config.seed}</span
                            >

                            {#if image.config.image_strength}
                                <span
                                    class="opacity-60 flex items-center gap-1"
                                >
                                    Strength
                                    <div
                                        class="tooltip tooltip-right"
                                        data-tip="Img2Img strength (how much the original image was changed)."
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            class="w-3 h-3 stroke-current opacity-50"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                            ></path></svg
                                        >
                                    </div>
                                </span>
                                <span class="font-mono text-right"
                                    >{image.config.image_strength}</span
                                >
                            {/if}

                            {#if image.config.controlnet}
                                <span
                                    class="opacity-60 flex items-center gap-1"
                                >
                                    ControlNet
                                    <div
                                        class="tooltip tooltip-right"
                                        data-tip="The ControlNet model used for guidance."
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            class="w-3 h-3 stroke-current opacity-50"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                            ></path></svg
                                        >
                                    </div>
                                </span>
                                <span
                                    class="font-mono text-right uppercase text-[10px]"
                                    >{image.config.controlnet}</span
                                >
                            {/if}
                        </div>
                    </div>

                    <div class="divider"></div>

                    <div>
                        <h3
                            class="text-xs font-bold uppercase tracking-widest opacity-40 mb-2"
                        >
                            Prompt
                        </h3>
                        <div
                            class="text-sm bg-base-300 p-3 rounded-lg border border-white/5 whitespace-pre-wrap"
                        >
                            {image.run.prompt}
                        </div>
                    </div>

                    {#if image.run.negative_prompt}
                        <div>
                            <h3
                                class="text-xs font-bold uppercase tracking-widest opacity-40 mb-2"
                            >
                                Neg Prompt
                            </h3>
                            <div
                                class="text-sm opacity-60 bg-base-300/50 p-2 rounded-lg italic"
                            >
                                {image.run.negative_prompt}
                            </div>
                        </div>
                    {/if}

                    <div class="divider"></div>

                    <div class="flex flex-col gap-2">
                        <button
                            class="btn btn-outline btn-secondary w-full"
                            onclick={() =>
                                window.open(
                                    getImageUrl(image.upscale_url || image.file_path),
                                    "_blank",
                                )}
                        >
                            Open Full Size
                        </button>
                        <a
                            href="/runs/{image.run_id}"
                            class="btn btn-ghost btn-sm w-full"
                            >Back to Gallery</a
                        >
                    </div>
                </div>
                </div>
            </div>

            <!-- Keyboard Help -->
            <div
                class="card bg-primary/10 border border-primary/20 p-4 text-[10px] leading-tight"
            >
                <div class="flex flex-col gap-2">
                    <div class="flex justify-between items-center opacity-70">
                        <span>Navigate</span>
                        <span class="flex gap-1">
                            <kbd class="kbd kbd-xs">←</kbd>
                            <kbd class="kbd kbd-xs">→</kbd>
                        </span>
                    </div>
                    <div class="flex justify-between items-center opacity-70">
                        <span>Quick Score (Quality + Next)</span>
                        <span class="flex gap-1">
                            <kbd class="kbd kbd-xs">1</kbd>
                            <span>-</span>
                            <kbd class="kbd kbd-xs">0</kbd>
                        </span>
                    </div>
                    <div class="flex justify-between items-center opacity-70">
                        <span>Toggle Compare</span>
                        <kbd class="kbd kbd-xs">C</kbd>
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>
