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

    interface ModelOption {
        id: string;
        name: string;
    }

    const defaultModelNameMap: Record<string, string> = {
        "sinkin.photo-real-v1": "SinkIn Photo Real v1",
        "sinkin.photo-real-v2": "SinkIn Photo Real v2",
        "sinkin.3d-artist": "SinkIn 3D Artist",
        "sinkin.anime-pro": "SinkIn Anime Pro",
    };

    let modelOptions = $state<ModelOption[]>([]);
    let loadingModels = $state(true);

    async function fetchModels() {
        try {
            const res = await fetch("http://localhost:8000/api/models");
            if (!res.ok) throw new Error("Failed to fetch models");
            const data = await res.json();
            if (Array.isArray(data.models) && data.models.length > 0) {
                modelOptions = data.models;
            }
        } catch (e) {
            console.warn("Model lookup failed", e);
        } finally {
            loadingModels = false;
        }
    }

    function formatModelName(modelId?: string | null) {
        if (!modelId) return "--";
        const match = modelOptions.find((m) => m.id === modelId);
        if (match) return match.name;
        return defaultModelNameMap[modelId] ?? modelId;
    }

    type UseAgainChoice = "yes" | "no" | "test_more" | "top_1pct" | null;

    type ScoreKey =
        | "score_overall"
        | "score_facial_detail_realism"
        | "score_body_proportions"
        | "score_complexity_artistry"
        | "score_composition_framing"
        | "score_lighting_color"
        | "score_resolution_clarity"
        | "score_style_consistency"
        | "score_prompt_adherence"
        | "score_artifacts";

    interface ScoreBlock {
        label: string;
        key: ScoreKey;
        help: string;
    }

    type CurationMarker = "trash" | "use_again" | "top_1pct";

    interface ImageDetail {
        id: string;
        run_id: string;
        file_path: string | null;
        upscale_url: string | null;
        inf_id: string | null;
        scores: {
            score_overall: number | null;
            score_facial_detail_realism: number | null;
            score_body_proportions: number | null;
            score_complexity_artistry: number | null;
            score_composition_framing: number | null;
            score_lighting_color: number | null;
            score_resolution_clarity: number | null;
            score_style_consistency: number | null;
            score_prompt_adherence: number | null;
            score_artifacts: number | null;
            use_again: UseAgainChoice;
            flaws: string | null; // JSON string
            curation_status: CurationMarker | null;
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
    let currentIndex = $derived(allImageIds.indexOf(page.params.image_id ?? ""));
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
    let autoAdvance = $state(true);
    const qualityScale = Array.from({ length: 5 }, (_, i) => i + 1);

    const scoreBlocks: ScoreBlock[] = [
        {
            key: "score_overall",
            label: "Overall Quality",
            help: "Primary 1-5 rating for this image.",
        },
        {
            key: "score_facial_detail_realism",
            label: "Facial Detail & Realism",
            help: "Eye depth, skin texture, expression believability.",
        },
        {
            key: "score_body_proportions",
            label: "Body Proportions & Anatomy",
            help: "Symmetry, musculature, anatomical accuracy.",
        },
        {
            key: "score_complexity_artistry",
            label: "Complexity & Artistic Quality",
            help: "Texture richness, fabric detail, layered rendering.",
        },
        {
            key: "score_composition_framing",
            label: "Composition & Framing",
            help: "Balance of elements, subject focus, background relevance.",
        },
        {
            key: "score_lighting_color",
            label: "Lighting & Color Accuracy",
            help: "Natural light, skin tones, cohesive palette.",
        },
        {
            key: "score_resolution_clarity",
            label: "Resolution & Clarity",
            help: "Sharpness, absence of pixelation, high fidelity.",
        },
        {
            key: "score_style_consistency",
            label: "Style Consistency",
            help: "Cohesive aesthetic (photoreal, stylized, etc.).",
        },
        {
            key: "score_prompt_adherence",
            label: "Prompt Adherence",
            help: "Contains all requested elements, aligns with brief.",
        },
        {
            key: "score_artifacts",
            label: "Artifacts",
            help: "Absence of blur, noise, discoloration, distortion.",
        },
    ];

    type UseAgainOption = Exclude<UseAgainChoice, null>;

    const useAgainOptions: {
        id: UseAgainOption;
        label: string;
        icon: string;
        tooltip: string;
    }[] = [
        {
            id: "yes",
            label: "Use Again",
            icon: "thumb_up",
            tooltip: "Reliable result worth repeating in future batches.",
        },
        {
            id: "test_more",
            label: "Test More",
            icon: "autorenew",
            tooltip: "Interesting but needs more experimentation or tweaks.",
        },
        {
            id: "no",
            label: "Trash",
            icon: "thumb_down",
            tooltip: "Fails the brief or contains major flaws – skip it.",
        },
        {
            id: "top_1pct",
            label: "Top 1%",
            icon: "diamond",
            tooltip: "Exceptional keeper. Add to highlight reel immediately.",
        },
    ];

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

    async function submitOverallScore(score: number, advance: boolean) {
        await updateScore({ score_overall: score });
        if (advance) {
            navigateNext();
        }
    }

    async function handlePanelQuality(score: number) {
        await submitOverallScore(score, autoAdvance);
    }

    async function handleOverallQuality(score: number) {
        await submitOverallScore(score, true);
    }

    async function handleScoreBlock(key: ScoreKey, value: number) {
        await updateScore({ [key]: value });
    }

    async function handleUseAgain(choice: UseAgainChoice) {
        await updateScore({ use_again: choice });
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

        if (e.key >= "1" && e.key <= "5") {
            handleOverallQuality(parseInt(e.key));
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
        fetchModels();
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
                                class="flex-1 win95-inset bg-black/5 flex items-center justify-center overflow-hidden relative"
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
                        class="flex-1 win95-inset bg-black/10 flex items-center justify-center overflow-hidden relative"
                    >
                        <img
                            src={getImageUrl(
                                !compareMode || !image.upscale_url
                                    ? image.file_path
                                    : image.upscale_url,
                            )}
                            alt="Generated artwork"
                            class="object-contain max-h-[80vh] w-full drop-shadow-[0_20px_60px_rgba(0,0,0,0.6)]"
                        />

                        <!-- Floating score badge -->
                        <div
                            class="absolute top-6 right-6 bg-black/70 border border-white text-white px-4 py-2 rounded-full flex items-center gap-2 font-pixel text-sm shadow-[0_4px_20px_rgba(0,0,0,0.6)]"
                        >
                            <span class="uppercase text-[9px] tracking-[0.2em]"
                                >Quality</span
                            >
                            <span class="text-2xl text-win-magenta"
                            >{image.scores.score_overall || "--"}</span
                        >
                        </div>

                        <!-- Desktop vertical scoring rail -->
                        <div
                            class="hidden xl:flex flex-col gap-1 absolute top-1/2 -translate-y-1/2 right-6 bg-black/60 backdrop-blur-md border border-white p-2 rounded-xl shadow-[0_12px_30px_rgba(0,0,0,0.6)]"
                        >
                            <span
                                class="text-[8px] uppercase text-white/80 tracking-[0.3em] mb-1 text-center"
                                >Set Score</span
                            >
                            {#each qualityScale as value}
                                <button
                                    onclick={() => handlePanelQuality(value)}
                                    class="w-10 h-10 flex items-center justify-center font-pixel text-lg border border-white transition-none {image
                                        .scores.score_overall === value
                                        ? 'bg-win-magenta text-white'
                                        : 'bg-[#c0c0c0] text-black hover:bg-white'}"
                                    aria-label={`Set quality ${value}`}
                                >
                                    {value}
                                </button>
                            {/each}
                        </div>

                        <!-- Mobile scoring bar -->
                        <div
                            class="xl:hidden absolute inset-x-4 bottom-6 bg-black/65 backdrop-blur-md border border-white rounded-lg p-2 shadow-[0_8px_30px_rgba(0,0,0,0.6)]"
                        >
                            <div
                                class="flex justify-between items-center text-[8px] uppercase text-white/70 mb-1"
                            >
                                <span>Tap to Rate</span>
                                <span>{image.scores.score_overall || "--"}</span>
                            </div>
                            <div class="flex flex-wrap gap-1 justify-center">
                                {#each qualityScale as value}
                                    <button
                                        onclick={() => handlePanelQuality(value)}
                                        class="w-8 h-8 flex items-center justify-center font-bold border border-white text-[10px] {image
                                            .scores.score_overall === value
                                            ? 'bg-win-magenta text-white'
                                            : 'bg-[#c0c0c0] text-black hover:bg-white'}"
                                        aria-label={`Set quality ${value}`}
                                    >
                                        {value}
                                    </button>
                                {/each}
                            </div>
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
                <div class="flex flex-col gap-3 p-2">
                    <div class="flex flex-wrap items-center justify-between gap-4">
                        <div class="flex items-center gap-3 pl-1">
                            <div class="flex items-center gap-3">
                                <span
                                    class="text-[10px] font-bold uppercase tracking-widest text-win-purple"
                                    >Quality:</span
                                >
                                <span
                                    class="win95-inset bg-white px-3 py-1 text-2xl font-pixel text-win-magenta min-w-[64px] text-center"
                                >
                                    {image.scores.score_overall || "--"}
                                </span>
                            </div>
                            <label
                                class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide cursor-pointer"
                            >
                                <input
                                    type="checkbox"
                                    bind:checked={autoAdvance}
                                    class="w-4 h-4 accent-win-magenta"
                                />
                                <span>Auto-advance</span>
                            </label>
                        </div>
                        <div class="flex gap-2 pr-1">
                            <a
                                href="/runs/{page.params.id}"
                                class="win95-btn h-8 px-3 text-[10px] font-bold uppercase flex items-center gap-2 bg-white no-underline text-black"
                            >
                                <span class="material-symbols-outlined text-[16px]"
                                    >grid_view</span
                                >
                                Gallery
                            </a>
                            <button
                                onclick={navigateNext}
                                class="win95-btn h-8 px-3 text-[10px] font-bold uppercase flex items-center gap-2 bg-win-purple text-white"
                            >
                                <span class="material-symbols-outlined text-[16px]"
                                    >arrow_forward</span
                                >
                                Next
                            </button>
                        </div>
                    </div>

                    <div class="flex items-center justify-between gap-2 flex-wrap">
                        <div class="flex gap-2">
                            {#each qualityScale as value}
                                <button
                                    onclick={() => handlePanelQuality(value)}
                                    class="w-10 h-10 flex items-center justify-center font-pixel text-lg border border-white transition-none {image
                                        .scores.score_overall === value
                                        ? 'bg-win-magenta text-white'
                                        : 'bg-[#c0c0c0] text-black hover:bg-white'}"
                                >
                                    {value}
                                </button>
                            {/each}
                        </div>
                        <div class="flex gap-2">
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
                                onclick={() => {
                                    if (!image) return;
                                    window.open(
                                        getImageUrl(
                                            image.upscale_url ||
                                                image.file_path,
                                        ),
                                        "_blank",
                                    );
                                }}
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

            <!-- Enhance Section (moved out of inspector) -->
            <div class="win95-window mx-4 mb-4 p-1">
                <div
                    class="bg-teal-700 text-white px-2 py-0.5 text-[9px] font-bold uppercase flex justify-between items-center mb-2"
                >
                    <span>UPSCALER_ENGINE.DLL</span>
                    <span class="material-symbols-outlined text-[14px]">auto_fix_high</span>
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
                        >
                            ESRGAN
                        </button>
                        <button
                            onclick={() => (upscaleType = "hires_fix")}
                            class="flex-1 h-7 text-[9px] font-bold uppercase transition-none {upscaleType ===
                            'hires_fix'
                                ? 'bg-win-purple text-white'
                                : 'bg-white text-black hover:bg-gray-100'}"
                        >
                            Hires Fix
                        </button>
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
                            <span class="loading loading-spinner h-4 w-4"></span>
                            WORKING...
                        {:else}
                            <span class="material-symbols-outlined text-[20px]">bolt</span>
                            Initiate Upscale
                        {/if}
                    </button>
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
                            {image.scores.score_overall || "--"}
                        </div>
                        <span class="text-[9px] uppercase font-bold opacity-60"
                            >Target Range: 1-5</span
                        >
                    </div>
                </div>

                <!-- Detailed Grading -->
                <div class="flex flex-col gap-2 p-2 win95-window">
                    <div
                        class="bg-blue-800 text-white px-2 py-0.5 text-[9px] font-bold uppercase flex justify-between items-center"
                    >
                        <span>Evaluation Matrix</span>
                        <span class="material-symbols-outlined text-[14px]"
                            >tune</span
                        >
                    </div>

                    <div class="grid grid-cols-1 gap-3">
                        {#each scoreBlocks as block}
                            <div class="bg-white/80 border border-gray-300 p-2 flex flex-col gap-2">
                                <div class="flex justify-between items-center text-[10px] font-bold uppercase">
                                    <div class="flex items-center gap-2 text-gray-600">
                                        <span>{block.label}</span>
                                        <span
                                            class="material-symbols-outlined text-[12px] opacity-40 cursor-help"
                                            title={block.help}
                                            >info</span
                                        >
                                    </div>
                                    <span class="font-pixel text-blue-700 text-base"
                                        >{image?.scores?.[block.key] || "--"}</span
                                    >
                                </div>
                                <div class="flex gap-1 flex-wrap">
                                    {#each qualityScale as value}
                                        <button
                                            onclick={() =>
                                                handleScoreBlock(block.key, value)}
                                            class="w-8 h-8 flex items-center justify-center text-[10px] font-bold border border-white transition-none {image
                                                ?.scores?.[block.key] === value
                                                ? 'bg-win-magenta text-white'
                                                : 'bg-[#c0c0c0] text-black hover:bg-white'}"
                                            aria-label={`Set ${block.label} to ${value}`}
                                        >
                                            {value}
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/each}
                    </div>

                    <hr class="border-t border-gray-400 my-2" />

                    <!-- Flaw Detector -->
                    <div class="flex flex-col gap-2">
                        <div
                            class="text-[10px] font-bold uppercase tracking-widest text-win-purple mb-1 tooltip-container relative group w-fit"
                        >
                            DEFECT_DETECTION
                            <span
                                class="material-symbols-outlined text-[10px] opacity-40 inline-block align-middle ml-1"
                                >help</span
                            >
                            <span
                                class="absolute left-0 bottom-full mb-1 w-48 bg-[#ffffe0] text-black border border-black p-2 text-[9px] font-normal normal-case shadow-[2px_2px_0_0_rgba(0,0,0,0.5)] z-50 hidden group-hover:block pointer-events-none"
                            >
                                Select all specific issues found in this
                                generation. Helps identify model weaknesses.
                            </span>
                        </div>
                        <div class="flex flex-wrap gap-1.5">
                            {#each ["Bad Hands", "Distorted Face", "Limb Fusion", "Artifacts", "Blurry", "Bleeding", "Cropped", "Text Error", "Watermark"] as flaw}
                                {@const currentFlaws = image?.scores?.flaws
                                    ? JSON.parse(image.scores.flaws)
                                    : []}
                                {@const isActive =
                                    currentFlaws.includes(flaw)}
                                <button
                                    onclick={() => {
                                        const newFlaws = isActive
                                            ? currentFlaws.filter(
                                                  (f: string) => f !== flaw,
                                              )
                                            : [...currentFlaws, flaw];
                                        updateScore({ flaws: newFlaws });
                                    }}
                                    class="px-2 py-0.5 border text-[9px] font-bold uppercase transition-none flex items-center gap-1
                                    {isActive
                                        ? 'bg-red-100 border-red-600 text-red-700 shadow-[inset_1px_1px_0_rgba(0,0,0,0.1)]'
                                        : 'bg-white border-gray-400 text-gray-500 hover:border-black hover:text-black'}"
                                >
                                    {#if isActive}<span
                                            class="material-symbols-outlined text-[10px]"
                                            >close</span
                                        >{/if}
                                    {flaw}
                                </button>
                            {/each}
                        </div>
                    </div>

                    <hr class="border-t border-gray-400 my-1" />

                    <!-- Use Again -->
                    <div class="flex flex-col gap-2">
                        <div
                            class="text-[10px] font-bold uppercase tracking-widest text-gray-600 mb-1"
                        >
                            USE AGAIN
                        </div>
                        <div class="grid grid-cols-3 gap-1">
                            {#each useAgainOptions as option}
                                {@const isSelected =
                                    image?.scores?.use_again === option.id}
                                <button
                                    onclick={() => handleUseAgain(option.id)}
                                    class="flex flex-col items-center justify-center gap-1 border text-[9px] font-bold uppercase py-2 px-1 transition-none {isSelected
                                        ? 'bg-win-magenta text-white border-black shadow-[inset_1px_1px_0_rgba(0,0,0,0.3)]'
                                        : 'bg-gray-100 text-gray-600 border-white border-b-gray-400 border-r-gray-400 hover:bg-white hover:text-black'}"
                                >
                                    <span
                                        class="material-symbols-outlined text-[14px]"
                                        >{option.icon}</span
                                    >
                                    <span class="text-[8px] text-center"
                                        >{option.label}</span
                                    >
                                </button>
                            {/each}
                        </div>
                    </div>

                </div>

                <!-- Param Stack -->
                {#if image?.config}
                    <div class="win95-window p-1">
                        <div
                            class="bg-gray-700 text-white px-2 py-0.5 text-[9px] font-bold uppercase flex justify-between items-center mb-2"
                        >
                            <span>CONFIG_STACK</span>
                            <span class="material-symbols-outlined text-[14px]">settings</span>
                        </div>
                        <div class="p-3 flex flex-col gap-3 text-[10px]">
                            <div class="grid grid-cols-2 gap-2">
                                <div class="win95-inset bg-gray-50 px-2 py-2 flex flex-col gap-1">
                                    <span class="text-[8px] uppercase font-bold opacity-50">Model</span>
                                    <span class="font-bold uppercase truncate"
                                        >{formatModelName(image.run.model_id)}</span
                                    >
                                </div>
                                <div class="win95-inset bg-gray-50 px-2 py-2 flex flex-col gap-1">
                                    <span class="text-[8px] uppercase font-bold opacity-50">Credit Cost</span>
                                    <span class="font-bold">
                                        {image.config.credit_cost != null
                                            ? `${image.config.credit_cost.toFixed(2)}`
                                            : "--"}{" "}
                                        cr
                                    </span>
                                </div>
                            </div>

                            <div class="grid grid-cols-2 gap-2">
                                <div class="win95-inset bg-gray-50 px-2 py-1 flex justify-between">
                                    <span class="opacity-60 uppercase font-bold">Steps</span>
                                    <span class="font-bold"
                                        >{image.config.steps ?? "--"}</span
                                    >
                                </div>
                                <div class="win95-inset bg-gray-50 px-2 py-1 flex justify-between">
                                    <span class="opacity-60 uppercase font-bold">CFG</span>
                                    <span class="font-bold"
                                        >{image.config.scale ?? "--"}</span
                                    >
                                </div>
                                <div class="win95-inset bg-gray-50 px-2 py-1 flex justify-between">
                                    <span class="opacity-60 uppercase font-bold">Width</span>
                                    <span class="font-bold">
                                        {image.config.width
                                            ? `${image.config.width}px`
                                            : "--"}
                                    </span>
                                </div>
                                <div class="win95-inset bg-gray-50 px-2 py-1 flex justify-between">
                                    <span class="opacity-60 uppercase font-bold">Height</span>
                                    <span class="font-bold">
                                        {image.config.height
                                            ? `${image.config.height}px`
                                            : "--"}
                                    </span>
                                </div>
                            </div>
                            <div
                                class="win95-inset bg-gray-50 px-2 py-2 flex flex-col gap-1 overflow-hidden"
                            >
                                <span class="text-[9px] uppercase font-bold opacity-40"
                                    >Scheduler_Engine</span
                                >
                                <span
                                    class="text-[10px] font-bold uppercase truncate italic"
                                    >{image.config.scheduler || "--"}</span
                                >
                            </div>
                            <div
                                class="win95-inset bg-gray-50 px-2 py-2 flex flex-col gap-1 overflow-hidden"
                            >
                                <span class="text-[9px] uppercase font-bold opacity-40">Seed_ID</span>
                                <span class="text-[10px] font-bold truncate font-mono"
                                    >{image.config.seed ?? "--"}</span
                                >
                            </div>
                        </div>
                    </div>
                {/if}

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
        transition: transform 0.1s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.5rem;
        border-radius: 9999px;
        background: rgba(255, 255, 255, 0.4);
        border: 2px solid #fff;
        box-shadow: 2px 2px 0 0 rgba(0, 0, 0, 1);
    }

    .range-retro {
        -webkit-appearance: none;
        appearance: none;
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
