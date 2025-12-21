<script lang="ts">
    import { browser } from "$app/environment";
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { toasts } from "$lib/stores/toasts";

    interface Model {
        id: string;
        name: string;
        cover_img?: string;
    }

    // Form State
    let name = $state("");
    let prompt = $state("");
    let negativePrompt = $state("");
    let useDefaultNeg = $state(true);
    let modelId = $state("yBG2r9O");
    let width = $state(512);
    let height = $state(768);
    let numImages = $state(4);
    let totalJobs = $state(1);
    let seed = $state(-1);

    // Models from API
    let models = $state<Model[]>([]);
    let selectedModel = $derived(models.find((m) => m.id === modelId));

    // Multi-select states
    let stepsInput = $state("30");
    let scaleInput = $state("7.5");
    let selectedSchedulers = $state<string[]>(["DPMSolverMultistep"]);

    // Img2Img / Base Image
    let initImageAssetId = $state<string | null>(null);
    let imageStrength = $state(0.75);
    let controlnet = $state("none");
    let uploadingFile = $state(false);
    let previewUrl = $state<string | null>(null);

    let loadingModels = $state(true);
    let submitting = $state(false);
    let executionProgress = $state({ current: 0, total: 0 });

    // Queue State
    let queuedItems = $state<any[]>([]);
    const QUEUE_STORAGE_KEY = "sinkinQueuedItems";

    const schedulerOptions = [
        "DPMSolverMultistep",
        "K_EULER_ANCESTRAL",
        "DDIM",
        "K_EULER",
        "PNDM",
        "KLMS",
    ];

    const defaultModels: Model[] = [
        { id: "yBG2r9O", name: "majicMIX realistic" },
        { id: "mGYMaD5", name: "AbsoluteReality" },
        { id: "4zdwGOB", name: "DreamShaper" },
        { id: "r2La2w2", name: "Realistic Vision" },
        { id: "K6KkkKl", name: "Deliberate" },
    ];

    async function fetchModels() {
        try {
            const res = await fetch("http://localhost:8000/api/models");
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to fetch models");
            }
            const data = await res.json();
            if (data.models && data.models.length > 0) {
                models = data.models;
            } else {
                models = defaultModels;
            }
        } catch (e: any) {
            console.error("Model fetch error:", e);
            toasts.error(`Model Sync Failed: ${e.message}`);
            models = defaultModels;
        } finally {
            loadingModels = false;
        }
    }

    async function handleFileUpload(e: Event) {
        const target = e.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;

        previewUrl = URL.createObjectURL(file);
        uploadingFile = true;
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("http://localhost:8000/api/assets", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            initImageAssetId = data.id;
            toasts.success("Base image uploaded successfully");
        } catch (e) {
            toasts.error("Failed to upload base image");
        } finally {
            uploadingFile = false;
        }
    }

    function removeAsset() {
        initImageAssetId = null;
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
        toasts.info("Asset removed");
    }

    function calculateJobCount(item: any) {
        const steps = item.stepsInput.split(",").length;
        const scales = item.scaleInput.split(",").length;
        const schedulers = item.selectedSchedulers.length;
        return steps * scales * schedulers * (item.totalJobs || 1);
    }

    function loadQueuedItems() {
        if (!browser) return [];
        try {
            const raw = localStorage.getItem(QUEUE_STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (err) {
            console.warn("Failed to parse saved queue", err);
            return [];
        }
    }

    function persistQueue(items: any[]) {
        if (!browser) return;
        const serialized = items.map(({ previewUrl: _ignore, ...rest }) => rest);
        localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(serialized));
    }

    function clearPersistedQueue() {
        if (!browser) return;
        localStorage.removeItem(QUEUE_STORAGE_KEY);
    }

    function hydrateQueueFromStorage() {
        const saved = loadQueuedItems();
        if (saved.length > 0) {
            queuedItems = saved;
            toasts.info(
                `Restored ${saved.length} buffered batch${saved.length > 1 ? "es" : ""}. Run them here or via the Dashboard.`,
            );
        }
    }

    function addToQueue() {
        if (!prompt) {
            toasts.warning("Please enter a prompt");
            return;
        }

        const item = {
            id: crypto.randomUUID(),
            name,
            prompt,
            negativePrompt,
            modelId,
            width,
            height,
            stepsInput,
            scaleInput,
            selectedSchedulers: [...selectedSchedulers],
            numImages,
            totalJobs,
            seed,
            useDefaultNeg,
            initImageAssetId,
            previewUrl,
            imageStrength,
            controlnet,
            modelTitle:
                models.find((m: Model) => m.id === modelId)?.name || modelId,
            coverImg: models.find((m: Model) => m.id === modelId)?.cover_img,
        };

        queuedItems = [...queuedItems, item];
        persistQueue(queuedItems);
        toasts.info(
            `Batch buffered (${calculateJobCount(
                item,
            )} jobs). Run from this page or process later on the Dashboard.`,
        );
        name = "";
    }

    function removeFromQueue(id: string) {
        queuedItems = queuedItems.filter((item) => item.id !== id);
        persistQueue(queuedItems);
        toasts.info("Batch removed from queue");
    }

    async function runExperiment() {
        if (queuedItems.length === 0) return;
        submitting = true;
        executionProgress = { current: 0, total: queuedItems.length };

        try {
            for (const item of queuedItems) {
                const steps_list = item.stepsInput
                    .split(",")
                    .map((s: string) => parseInt(s.trim()))
                    .filter((n: number) => !isNaN(n));
                const scale_list = item.scaleInput
                    .split(",")
                    .map((s: string) => parseFloat(s.trim()))
                    .filter((n: number) => !isNaN(n));

                const payload = {
                    name: item.name,
                    prompt: item.prompt,
                    negative_prompt: item.negativePrompt,
                    model_id: item.modelId,
                    width: item.width,
                    height: item.height,
                    steps_list,
                    scale_list,
                    scheduler_list: item.selectedSchedulers,
                    num_images: item.numImages,
                    total_jobs: item.totalJobs,
                    seed: item.seed,
                    use_default_neg: item.useDefaultNeg,
                    init_image_asset_id: item.initImageAssetId,
                    image_strength: item.imageStrength,
                    controlnet:
                        item.controlnet === "none" ? null : item.controlnet,
                };

                const res = await fetch("http://localhost:8000/api/runs", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!res.ok) throw new Error("Failed to create run");
                executionProgress.current++;
            }

            toasts.success(
                `Experiment started with ${queuedItems.length} batches`,
            );
            queuedItems = [];
            clearPersistedQueue();
            goto("/?autorun=true");
        } catch (e: any) {
            toasts.error(e.message || "Error creating batch experiment");
        } finally {
            submitting = false;
        }
    }

    function toggleScheduler(s: string) {
        if (selectedSchedulers.includes(s)) {
            selectedSchedulers = selectedSchedulers.filter(
                (item) => item !== s,
            );
        } else {
            selectedSchedulers = [...selectedSchedulers, s];
        }
    }

    onMount(() => {
        fetchModels();
        hydrateQueueFromStorage();
    });
</script>

<div class="flex flex-col h-full overflow-hidden font-mono bg-[#d4d0c8]">
    <!-- Window Header -->
    <div class="win95-title-bar shrink-0">
        <span class="flex items-center gap-2"
            ><span class="material-symbols-outlined text-[16px]">add_box</span> C:\SYSTEM\NEW_EXPERIMENT.EXE</span
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

    <div class="flex-1 overflow-y-auto p-6 custom-scrollbar bg-checkered">
        <div class="max-w-6xl mx-auto flex flex-col lg:flex-row gap-6">
            <!-- Left Panel: Configuration Form -->
            <div class="flex-1 flex flex-col gap-6">
                <!-- Experiment Identity -->
                <div class="win95-window p-1">
                    <div
                        class="bg-blue-800 text-white px-2 py-0.5 text-[10px] font-bold uppercase flex justify-between items-center mb-4"
                    >
                        <span>EXPERIMENT_IDENTITY</span>
                        <span class="material-symbols-outlined text-[16px]"
                            >fingerprint</span
                        >
                    </div>
                    <div class="p-4 space-y-5">
                        <div class="flex flex-col gap-1">
                            <label
                                for="experiment-name"
                                class="text-[10px] font-bold uppercase text-gray-700"
                                >Experiment Name (Optional)</label
                            >
                            <input
                                id="experiment-name"
                                bind:value={name}
                                type="text"
                                class="win95-input h-8 px-2"
                                placeholder="e.g., Portrait_Study_01"
                            />
                        </div>
                        <div class="flex flex-col gap-1">
                            <div
                                class="flex justify-between items-center text-[10px] font-bold uppercase text-gray-700"
                            >
                                <span>Core Prompt Cluster</span>
                                <span class="text-win-purple italic"
                                    >REQUIRED*</span
                                >
                            </div>
                            <textarea
                                bind:value={prompt}
                                class="win95-inset w-full h-32 p-3 text-sm bg-white font-mono leading-relaxed"
                                placeholder="An interior photo of a futuristic laboratory, soft lighting, 8k..."
                            ></textarea>
                        </div>
                        <div
                            class="flex justify-between items-center text-[10px] font-bold uppercase text-gray-700"
                        >
                            <span>Negative Prompt Null-Set</span>
                            <label
                                class="flex items-center gap-1 cursor-pointer hover:text-win-purple"
                            >
                                <input
                                    type="checkbox"
                                    bind:checked={useDefaultNeg}
                                    class="accent-win-purple"
                                />
                                <span>Append System Default</span>
                            </label>
                        </div>
                        <textarea
                            bind:value={negativePrompt}
                            class="win95-inset w-full h-20 p-2 text-xs bg-white/80 font-mono italic"
                            placeholder="blurry, distorted, low quality..."
                        ></textarea>
                    </div>
                </div>

                <!-- Technical Parameters -->
                <div class="win95-window p-1">
                    <div
                        class="bg-win-purple text-white px-2 py-0.5 text-[10px] font-bold uppercase flex justify-between items-center mb-4"
                    >
                        <span>TECHNICAL_PARAMS.DLL</span>
                        <span class="material-symbols-outlined text-[16px]"
                            >settings_input_component</span
                        >
                    </div>
                    <div class="p-4 space-y-6">
                        <!-- Top Row: Model Selection (Full Width to avoid overlap) -->
                        <div class="flex flex-col gap-2">
                            <label
                                for="model-select"
                                class="text-[10px] font-bold uppercase text-gray-700 underline"
                                >Inference Engine (Model)</label
                            >
                            <div class="flex flex-col sm:flex-row gap-4">
                                <div class="flex-1 flex flex-col gap-2 min-w-0">
                                    <select
                                        id="model-select"
                                        bind:value={modelId}
                                        class="win95-input h-10 px-1 text-xs w-full"
                                    >
                                        {#if loadingModels}
                                            <option>LOADING_DATA...</option>
                                        {:else}
                                            {#each models as model}
                                                <option value={model.id}
                                                    >{model.name}</option
                                                >
                                            {/each}
                                        {/if}
                                    </select>
                                    <div
                                        class="win95-inset bg-white p-2 min-h-[40px] flex items-center"
                                    >
                                        <span
                                            class="text-[9px] font-bold text-win-purple uppercase"
                                            >ID: {modelId}</span
                                        >
                                    </div>
                                </div>

                                <!-- Model Cover Preview -->
                                <div
                                    class="w-full sm:w-32 flex flex-col shrink-0"
                                >
                                    <div
                                        class="win95-window p-0.5 bg-[#d4d0c8]"
                                    >
                                        <div
                                            class="bg-blue-900 px-1.5 py-0.5 flex justify-between items-center mb-0.5"
                                        >
                                            <span
                                                class="text-[8px] text-white font-bold uppercase truncate"
                                                >PREVIEW.BMP</span
                                            >
                                            <div
                                                class="w-2 h-2 bg-[#c0c0c0] border border-white border-b-black border-r-black"
                                            ></div>
                                        </div>
                                        <div
                                            class="w-full h-32 sm:h-44 win95-inset bg-[#808080] flex items-center justify-center overflow-hidden relative group"
                                        >
                                            {#if selectedModel?.cover_img}
                                                <img
                                                    src={selectedModel.cover_img}
                                                    alt={selectedModel.name}
                                                    class="w-full h-full object-cover transition-transform group-hover:scale-110"
                                                />
                                                <div
                                                    class="absolute inset-0 bg-black/10 opacity-0 group-hover:opacity-100 transition-opacity"
                                                ></div>
                                            {:else}
                                                <div
                                                    class="flex flex-col items-center justify-center text-[#c0c0c0] p-2 text-center"
                                                >
                                                    <span
                                                        class="material-symbols-outlined text-2xl opacity-50"
                                                        >image</span
                                                    >
                                                    <span
                                                        class="text-[7px] uppercase mt-1 font-bold"
                                                        >NO_SYSTEM_ASSET</span
                                                    >
                                                </div>
                                            {/if}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Bottom Grid: Numerical Parameters -->
                        <div
                            class="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4 border-t border-gray-300/50"
                        >
                            <div class="space-y-4">
                                <div class="flex flex-col gap-1">
                                    <span
                                        class="text-[10px] font-bold uppercase text-gray-700 underline"
                                        >Resolution (WxH)</span
                                    >
                                    <div class="grid grid-cols-2 gap-2">
                                        <input
                                            id="resolution-width"
                                            bind:value={width}
                                            type="number"
                                            step="8"
                                            class="win95-input h-8 px-2 text-xs"
                                        />
                                        <input
                                            id="resolution-height"
                                            bind:value={height}
                                            type="number"
                                            step="8"
                                            class="win95-input h-8 px-2 text-xs"
                                        />
                                    </div>
                                </div>
                                <div class="flex flex-col gap-1">
                                    <label
                                        for="images-per-call"
                                        class="text-[10px] font-bold uppercase text-gray-700 underline"
                                        >Images per Engine Call</label
                                    >
                                    <div class="flex items-center gap-4">
                                        <input
                                            id="images-per-call"
                                            bind:value={numImages}
                                            type="range"
                                            min="1"
                                            max="4"
                                            class="flex-1 accent-win-magenta"
                                        />
                                        <span
                                            class="win95-inset bg-white px-2 py-0.5 font-pixel text-lg text-win-magenta"
                                            >{numImages}</span
                                        >
                                    </div>
                                </div>
                            </div>

                            <div class="space-y-4">
                                <div class="flex flex-col gap-1">
                                    <label
                                        for="seed-input"
                                        class="text-[10px] font-bold uppercase text-gray-700 underline"
                                        >Seed Initialization</label
                                    >
                                    <input
                                        id="seed-input"
                                        bind:value={seed}
                                        type="number"
                                        class="win95-input h-8 px-2 font-mono text-xs"
                                    />
                                    <span
                                        class="text-[8px] text-gray-500 italic mt-1"
                                        >(-1 FOR_RANDOM_DISTRIBUTION)</span
                                    >
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Matrix Testing -->
                <div class="win95-window p-1">
                    <div
                        class="bg-teal-700 text-white px-2 py-0.5 text-[10px] font-bold uppercase flex justify-between items-center mb-4"
                    >
                        <span>COMBINATORIAL_MATRIX_CONFIG</span>
                        <span class="material-symbols-outlined text-[16px]"
                            >grid_on</span
                        >
                    </div>
                    <div class="p-4 space-y-6">
                        <div class="grid grid-cols-2 gap-8">
                            <div class="flex flex-col gap-1">
                                <label
                                    for="steps-stack"
                                    class="text-[10px] font-bold uppercase text-gray-700 underline"
                                    >Steps Stack</label
                                >
                                <input
                                    id="steps-stack"
                                    bind:value={stepsInput}
                                    type="text"
                                    class="win95-input h-10 px-2 font-mono text-sm"
                                    placeholder="20, 30, 40"
                                />
                                <span class="text-[8px] text-gray-500 italic"
                                    >COMMA_SEPARATED_LIST</span
                                >
                            </div>
                            <div class="flex flex-col gap-1">
                                <label
                                    for="cfg-scale"
                                    class="text-[10px] font-bold uppercase text-gray-700 underline"
                                    >CFG_Scale Array</label
                                >
                                <input
                                    id="cfg-scale"
                                    bind:value={scaleInput}
                                    type="text"
                                    class="win95-input h-10 px-2 font-mono text-sm"
                                    placeholder="7, 9, 12"
                                />
                            </div>
                        </div>
                        <div class="flex flex-col gap-2">
                            <span
                                class="text-[10px] font-bold uppercase text-gray-700 underline"
                                >Active Schedulers</span
                            >
                            <div class="flex flex-wrap gap-2">
                                {#each schedulerOptions as s}
                                    <button
                                        type="button"
                                        onclick={() => toggleScheduler(s)}
                                        class="h-8 px-3 text-[9px] font-bold uppercase transition-none {selectedSchedulers.includes(
                                            s,
                                        )
                                            ? 'win95-btn bg-win-magenta text-white border-white border-b-black border-r-black'
                                            : 'win95-btn bg-[#c0c0c0] text-black hover:bg-white'}"
                                    >
                                        {s}
                                    </button>
                                {/each}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Panel: Queue & Assets -->
            <div class="w-full lg:w-[400px] flex flex-col gap-6">
                <!-- Base Image Asset -->
                <div class="win95-window p-1">
                    <div
                        class="bg-gray-700 text-white px-2 py-0.5 text-[10px] font-bold uppercase flex justify-between items-center mb-4"
                    >
                        <span>ASSET_INJECTION (IMG2IMG)</span>
                        <span class="material-symbols-outlined text-[16px]"
                            >image_search</span
                        >
                    </div>
                    <div class="p-4 space-y-5">
                        <div class="flex flex-col gap-2">
                            <input
                                type="file"
                                accept="image/*"
                                onchange={handleFileUpload}
                                class="text-[10px] font-bold underline cursor-pointer"
                            />
                            {#if uploadingFile}
                                <div class="bg-gray-200 h-1 overflow-hidden">
                                    <div
                                        class="bg-blue-800 h-full w-1/2 animate-pulse"
                                    ></div>
                                </div>
                            {/if}
                        </div>

                        {#if previewUrl}
                            <div
                                class="win95-inset bg-black/5 p-1 flex justify-center relative group"
                            >
                                <img
                                    src={previewUrl}
                                    alt="Preview"
                                    class="max-w-full h-32 object-contain"
                                />
                                <button
                                    onclick={removeAsset}
                                    class="absolute top-1 right-1 bg-red-600 text-white p-1 hover:bg-red-700 shadow-[1px_1px_0_0_black] flex items-center justify-center"
                                    title="Remove Asset"
                                >
                                    <span
                                        class="material-symbols-outlined text-[16px]"
                                        >close</span
                                    >
                                </button>
                            </div>
                            <div class="space-y-3">
                                <div class="flex flex-col gap-1">
                                    <div
                                        class="flex justify-between items-center text-[10px] font-bold"
                                    >
                                        <span>INFLUENCE_STRENGTH</span>
                                        <span
                                            class="font-pixel text-win-magenta text-sm"
                                            >{imageStrength}</span
                                        >
                                    </div>
                                    <input
                                        bind:value={imageStrength}
                                        type="range"
                                        min="0"
                                        max="1"
                                        step="0.05"
                                        class="accent-win-magenta"
                                    />
                                </div>
                                <div class="flex flex-col gap-1">
                                    <label
                                        for="controlnet-select"
                                        class="text-[10px] font-bold uppercase"
                                        >ControlNet_Module</label
                                    >
                                    <select
                                        id="controlnet-select"
                                        bind:value={controlnet}
                                        class="win95-input h-8 px-1 text-xs"
                                    >
                                        <option value="none"
                                            >NONE (STD_IMG2IMG)</option
                                        >
                                        <option value="canny">CANNY</option>
                                        <option value="depth">DEPTH</option>
                                        <option value="openpose"
                                            >OPENPOSE</option
                                        >
                                    </select>
                                </div>
                            </div>
                        {/if}
                    </div>
                </div>

                <!-- Final Payload Control -->
                <div class="win95-window grow flex flex-col p-1">
                    <div
                        class="bg-black text-white px-2 py-0.5 text-[10px] font-bold uppercase flex justify-between items-center mb-4"
                    >
                        <span>EXECUTION_BUFFER</span>
                        <span class="material-symbols-outlined text-[16px]"
                            >queue_play_next</span
                        >
                    </div>

                    <div class="p-4 flex flex-col gap-5 flex-1">
                        <div class="flex flex-col gap-1">
                            <label
                                for="total-jobs"
                                class="text-[10px] font-bold uppercase text-gray-700 underline"
                                >Batch Run Count</label
                            >
                            <input
                                id="total-jobs"
                                bind:value={totalJobs}
                                type="number"
                                min="1"
                                max="100"
                                class="win95-input h-10 px-2 font-pixel text-xl text-blue-700"
                            />
                            <span class="text-[8px] text-gray-500 italic"
                                >TOTAL_REPEAT_CYCLES</span
                            >
                        </div>

                        <button
                            type="button"
                            onclick={addToQueue}
                            class="win95-btn h-12 w-full bg-[#c0c0c0] text-black font-bold uppercase text-xs flex items-center justify-center gap-2 hover:bg-white active:bg-gray-400"
                            disabled={submitting || !prompt}
                        >
                            <span class="material-symbols-outlined text-[20px]"
                                >add_circle</span
                            > Add To Buffer
                        </button>

                        <div
                            class="flex-1 win95-inset bg-gray-50 flex flex-col p-2 overflow-hidden"
                        >
                            <div class="mb-2">
                                <h3
                                    class="text-[10px] font-bold uppercase opacity-60"
                                >
                                    Queued_Operations [{queuedItems.length}]
                                </h3>
                                <p class="text-[9px] text-gray-500 italic">
                                    Buffer autosaves locally. Click "Run Experiment" here or head to the Dashboard to execute when ready.
                                </p>
                            </div>
                            <div
                                class="flex-1 overflow-y-auto custom-scrollbar space-y-2"
                            >
                                {#each queuedItems as item (item.id)}
                                    <div
                                        class="bg-white border border-gray-300 p-2 text-[9px] flex gap-2 items-start"
                                    >
                                        {#if item.coverImg}
                                            <div
                                                class="w-10 h-14 border border-white border-b-black border-r-black bg-[#808080] shrink-0 overflow-hidden"
                                            >
                                                <img
                                                    src={item.coverImg}
                                                    alt=""
                                                    class="w-full h-full object-cover"
                                                />
                                            </div>
                                        {/if}
                                        <div class="flex-1 min-w-0">
                                            <div class="font-bold truncate">
                                                {item.name || "UNNAMED_BATCH"}
                                            </div>
                                            <div class="opacity-60 truncate">
                                                P: "{item.prompt}"
                                            </div>
                                            <div
                                                class="text-[8px] text-blue-800 font-bold mt-1"
                                            >
                                                EST_JOBS: {calculateJobCount(
                                                    item,
                                                )}
                                            </div>
                                        </div>
                                        <button
                                            onclick={() =>
                                                removeFromQueue(item.id)}
                                            class="text-red-700 hover:bg-red-50 p-1"
                                        >
                                            <span
                                                class="material-symbols-outlined text-[16px]"
                                                >delete</span
                                            >
                                        </button>
                                    </div>
                                {/each}
                                {#if queuedItems.length === 0}
                                    <div
                                        class="flex-1 flex flex-col items-center justify-center opacity-20 py-8"
                                    >
                                        <span
                                            class="material-symbols-outlined text-4xl"
                                            >inventory_2</span
                                        >
                                        <span
                                            class="text-[10px] uppercase font-bold mt-2"
                                            >Buffer_Empty</span
                                        >
                                    </div>
                                {/if}
                            </div>
                        </div>

                        <button
                            type="button"
                            onclick={runExperiment}
                            class="win95-btn h-14 w-full bg-blue-800 text-white font-bold uppercase text-sm flex items-center justify-center gap-3 active:bg-blue-900 border-white"
                            disabled={submitting || queuedItems.length === 0}
                        >
                            {#if submitting}
                                <span class="loading loading-spinner h-5 w-5"
                                ></span>
                                UPLOADING [{executionProgress.current}/{executionProgress.total}]
                            {:else}
                                <span
                                    class="material-symbols-outlined text-[24px]"
                                    >rocket_launch</span
                                > Initiate Experiment
                            {/if}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
