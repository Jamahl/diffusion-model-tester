<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { toasts } from "$lib/stores/toasts";

    interface Model {
        id: string;
        title: string;
    }

    // Form State
    let name = $state("");
    let prompt = $state("");
    let negativePrompt = $state("");
    let useDefaultNeg = $state(true);
    let modelId = $state("yBG2r9O"); // Default to majicMIX realistic
    let width = $state(512);
    let height = $state(768);
    let numImages = $state(4);
    let totalJobs = $state(1);
    let seed = $state(-1);

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

    // Models from API
    let models = $state<Model[]>([]);
    let loadingModels = $state(true);
    let submitting = $state(false);
    let executionProgress = $state({ current: 0, total: 0 });

    // Queue State
    let queuedItems = $state<any[]>([]);

    const schedulerOptions = [
        "DPMSolverMultistep",
        "K_EULER_ANCESTRAL",
        "DDIM",
        "K_EULER",
        "PNDM",
        "KLMS",
    ];

    const defaultModels = [
        { id: "yBG2r9O", title: "majicMIX realistic" },
        { id: "mGYMaD5", title: "AbsoluteReality" },
        { id: "4zdwGOB", title: "DreamShaper" },
        { id: "r2La2w2", title: "Realistic Vision" },
        { id: "K6KkkKl", title: "Deliberate" },
    ];

    async function fetchModels() {
        try {
            const res = await fetch("http://localhost:8000/api/models");
            if (!res.ok) throw new Error("API Key missing");
            const data = await res.json();
            if (data.models && data.models.length > 0) {
                models = data.models;
            } else {
                models = defaultModels;
            }
        } catch (e) {
            console.log("Using fallback models (API Key likely missing)");
            models = defaultModels;
        } finally {
            loadingModels = false;
        }
    }

    async function handleFileUpload(e: Event) {
        const target = e.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;

        // Preview
        previewUrl = URL.createObjectURL(file);

        // Upload
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

    function calculateJobCount(item: any) {
        const steps = item.stepsInput.split(",").length;
        const scales = item.scaleInput.split(",").length;
        const schedulers = item.selectedSchedulers.length;
        return steps * scales * schedulers * (item.totalJobs || 1);
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
            initImageAssetId,
            previewUrl,
            imageStrength,
            controlnet,
            modelTitle:
                models.find((m: Model) => m.id === modelId)?.title || modelId,
        };

        queuedItems = [...queuedItems, item];
        toasts.info(`Batch added to queue (${calculateJobCount(item)} jobs)`);
        // Keep form values as requested, but maybe clear the name if it was specific
        name = "";
    }

    function removeFromQueue(id: string) {
        queuedItems = queuedItems.filter((item) => item.id !== id);
        toasts.info("Batch removed from queue");
    }

    function handleSubmit(e: Event) {
        e.preventDefault();
        addToQueue();
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
            goto("/");
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

    onMount(fetchModels);
</script>

<div class="max-w-4xl mx-auto pb-20">
    <div class="flex items-center justify-between mb-8">
        <div>
            <h1 class="text-3xl font-bold font-display">New Experiment</h1>
            <p class="text-base-content/60">
                Define parameters for your generation batch.
            </p>
        </div>
    </div>

    <form onsubmit={handleSubmit} class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Main Config -->
        <div class="md:col-span-2 space-y-6">
            <div class="card bg-base-200 shadow-xl">
                <div class="card-body gap-4">
                    <div class="form-control w-full">
                        <label class="label">
                            <span
                                class="label-text font-semibold flex items-center gap-2"
                            >
                                Prompt
                                <div
                                    class="tooltip tooltip-right"
                                    data-tip="The core text description of what you want to see. Be descriptive and specific."
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        class="w-4 h-4 stroke-current opacity-50"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path></svg
                                    >
                                </div>
                            </span>
                        </label>
                        <textarea
                            bind:value={prompt}
                            class="textarea textarea-bordered h-32 text-lg"
                            placeholder="An interior photo of a futuristic laboratory, soft lighting, 8k..."
                            required
                        ></textarea>
                    </div>

                    <div class="form-control w-full">
                        <label class="label">
                            <span
                                class="label-text font-semibold flex items-center gap-2"
                            >
                                Negative Prompt
                                <div
                                    class="tooltip tooltip-right"
                                    data-tip="Describe what to exclude from the image (e.g., 'blurry, low quality')."
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        class="w-4 h-4 stroke-current opacity-50"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path></svg
                                    >
                                </div>
                            </span>
                        </label>
                        <textarea
                            bind:value={negativePrompt}
                            class="textarea textarea-bordered h-24 text-sm"
                            placeholder="blurry, distorted, low quality..."
                        ></textarea>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div class="form-control">
                            <label class="label">
                                <span
                                    class="label-text font-semibold flex items-center gap-2"
                                >
                                    Model
                                    <div
                                        class="tooltip tooltip-top"
                                        data-tip="The underlying AI model. Different models are trained on different styles (Photorealistic, Anime, etc.)."
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            class="w-4 h-4 stroke-current opacity-50"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                            ></path></svg
                                        >
                                    </div>
                                </span>
                            </label>
                            <select
                                bind:value={modelId}
                                class="select select-bordered"
                                disabled={loadingModels}
                            >
                                {#if loadingModels}
                                    <option>Loading models...</option>
                                {:else}
                                    {#each models as model}
                                        <option value={model.id}
                                            >{model.title}</option
                                        >
                                    {/each}
                                {/if}
                            </select>
                        </div>
                        <div class="form-control">
                            <label class="label">
                                <span
                                    class="label-text font-semibold flex items-center gap-2"
                                >
                                    Seed
                                    <div
                                        class="tooltip tooltip-top"
                                        data-tip="Starting point for generation. -1 is random. Use a fixed number to reproduce the exact same image."
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            class="w-4 h-4 stroke-current opacity-50"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                            ></path></svg
                                        >
                                    </div>
                                </span>
                            </label>
                            <input
                                bind:value={seed}
                                type="number"
                                class="input input-bordered font-mono"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <!-- Base Image / Img2Img Section -->
            <div class="card bg-base-200 shadow-xl">
                <div class="card-body">
                    <h2 class="card-title text-sm uppercase opacity-50 mb-4">
                        Base Image (img2img)
                    </h2>
                    <div class="flex flex-col md:flex-row gap-6">
                        <div class="flex-1">
                            <div class="form-control">
                                <label class="label">
                                    <span class="label-text"
                                        >Select or drop image</span
                                    >
                                    {#if initImageAssetId}
                                        <span class="badge badge-success"
                                            >Uploaded</span
                                        >
                                    {/if}
                                </label>
                                <input
                                    type="file"
                                    accept="image/*"
                                    onchange={handleFileUpload}
                                    class="file-input file-input-bordered w-full"
                                    disabled={uploadingFile}
                                />
                                {#if uploadingFile}
                                    <progress
                                        class="progress progress-primary w-full mt-2"
                                    ></progress>
                                {/if}
                            </div>

                            {#if initImageAssetId}
                                <div class="grid grid-cols-2 gap-4 mt-6">
                                    <div class="form-control">
                                        <label class="label">
                                            <span
                                                class="label-text text-xs flex items-center gap-2"
                                            >
                                                Strength
                                                <div
                                                    class="tooltip tooltip-top"
                                                    data-tip="How much to change the base image. 0.0 is no change, 1.0 is completely new image."
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
                                            <span class="badge badge-sm"
                                                >{imageStrength}</span
                                            >
                                        </label>
                                        <input
                                            bind:value={imageStrength}
                                            type="range"
                                            min="0"
                                            max="1"
                                            step="0.05"
                                            class="range range-xs"
                                        />
                                    </div>
                                    <div class="form-control">
                                        <label class="label">
                                            <span
                                                class="label-text text-xs flex items-center gap-2"
                                            >
                                                ControlNet
                                                <div
                                                    class="tooltip tooltip-top"
                                                    data-tip="Adds structural constraints (like edges or poses) to guide the generation using the base image."
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
                                        </label>
                                        <select
                                            bind:value={controlnet}
                                            class="select select-sm select-bordered"
                                        >
                                            <option value="none"
                                                >None (Standard Img2Img)</option
                                            >
                                            <option value="canny">Canny</option>
                                            <option value="depth">Depth</option>
                                            <option value="openpose"
                                                >OpenPose</option
                                            >
                                        </select>
                                    </div>
                                </div>
                            {/if}
                        </div>

                        {#if previewUrl}
                            <div
                                class="w-full md:w-32 aspect-square rounded-lg overflow-hidden bg-base-300 border border-white/10 shrink-0"
                            >
                                <img
                                    src={previewUrl}
                                    alt="Preview"
                                    class="w-full h-full object-cover"
                                />
                            </div>
                        {/if}
                    </div>
                </div>
            </div>

            <div class="card bg-base-200 shadow-xl">
                <div class="card-body">
                    <h2 class="card-title text-sm uppercase opacity-50 mb-2">
                        Combination Settings
                    </h2>
                    <div class="grid grid-cols-2 gap-6">
                        <div class="form-control">
                            <label class="label">
                                <span
                                    class="label-text font-semibold flex items-center gap-2"
                                >
                                    Steps
                                    <div
                                        class="tooltip tooltip-top"
                                        data-tip="Number of refinement iterations. More steps (30-50) increase quality but take longer to generate. Enter multiple values separated by commas for batch testing."
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            class="w-4 h-4 stroke-current opacity-50"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                            ></path></svg
                                        >
                                    </div>
                                </span>
                                <span class="label-text-alt opacity-50"
                                    >CSV allowed</span
                                >
                            </label>
                            <input
                                bind:value={stepsInput}
                                type="text"
                                class="input input-bordered"
                                placeholder="20, 30, 40"
                            />
                        </div>
                        <div class="form-control">
                            <label class="label">
                                <span
                                    class="label-text font-semibold flex items-center gap-2"
                                >
                                    CFG Scale
                                    <div
                                        class="tooltip tooltip-top"
                                        data-tip="Classifier Free Guidance. Higher values (7-12) force the model to follow the prompt more strictly. Enter multiple values separated by commas for batch testing."
                                    >
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            class="w-4 h-4 stroke-current opacity-50"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                            ></path></svg
                                        >
                                    </div>
                                </span>
                                <span class="label-text-alt opacity-50"
                                    >CSV allowed</span
                                >
                            </label>
                            <input
                                bind:value={scaleInput}
                                type="text"
                                class="input input-bordered"
                                placeholder="7, 9, 12"
                            />
                        </div>
                    </div>

                    <div class="form-control mt-4">
                        <label class="label">
                            <span
                                class="label-text font-semibold flex items-center gap-2"
                            >
                                Schedulers
                                <div
                                    class="tooltip tooltip-top"
                                    data-tip="The algorithm used to denoise the image. Different schedulers produce subtle styling variations. Select multiple to test across different algorithms."
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        class="w-4 h-4 stroke-current opacity-50"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path></svg
                                    >
                                </div>
                            </span>
                        </label>
                        <div class="flex flex-wrap gap-2">
                            {#each schedulerOptions as s}
                                <button
                                    type="button"
                                    onclick={() => toggleScheduler(s)}
                                    class="btn btn-sm {selectedSchedulers.includes(
                                        s,
                                    )
                                        ? 'btn-primary'
                                        : 'btn-outline opacity-50'}"
                                >
                                    {s}
                                </button>
                            {/each}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sidebar Controls -->
        <div class="space-y-6">
            <div class="card bg-base-200 shadow-xl">
                <div class="card-body gap-4">
                    <h2 class="card-title text-sm uppercase opacity-50">
                        Image Settings
                    </h2>
                    <div class="grid grid-cols-2 gap-3">
                        <div class="form-control">
                            <label class="label">
                                <span
                                    class="label-text text-xs flex items-center gap-2"
                                >
                                    Width
                                    <div
                                        class="tooltip tooltip-top"
                                        data-tip="Width of the generated image. Must be a multiple of 8."
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
                            </label>
                            <input
                                bind:value={width}
                                type="number"
                                step="8"
                                class="input input-sm input-bordered"
                            />
                        </div>
                        <div class="form-control">
                            <label class="label">
                                <span
                                    class="label-text text-xs flex items-center gap-2"
                                >
                                    Height
                                    <div
                                        class="tooltip tooltip-top"
                                        data-tip="Height of the generated image. Must be a multiple of 8."
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
                            </label>
                            <input
                                bind:value={height}
                                type="number"
                                step="8"
                                class="input input-sm input-bordered"
                            />
                        </div>
                    </div>

                    <div class="form-control">
                        <label class="label">
                            <span
                                class="label-text font-semibold text-xs flex items-center gap-2"
                            >
                                Images per Call
                                <div
                                    class="tooltip tooltip-top"
                                    data-tip="Number of images to generate in a single batch (max 4)."
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
                            <span class="badge badge-sm">{numImages}</span>
                        </label>
                        <input
                            bind:value={numImages}
                            type="range"
                            min="1"
                            max="4"
                            class="range range-xs range-primary"
                        />
                    </div>

                    <div class="form-control">
                        <label class="label">
                            <span
                                class="label-text font-semibold text-xs flex items-center gap-2"
                            >
                                Total Parallel Jobs
                                <div
                                    class="tooltip tooltip-top"
                                    data-tip="How many separate batches to run in this experiment. All combinations of Steps, CFG, and Schedulers will be multiplied by this."
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
                            <span class="badge badge-sm badge-secondary"
                                >{totalJobs}</span
                            >
                        </label>
                        <input
                            bind:value={totalJobs}
                            type="number"
                            min="1"
                            max="100"
                            class="input input-bordered"
                        />
                    </div>

                    <div class="divider"></div>

                    <button
                        type="button"
                        onclick={addToQueue}
                        class="btn btn-primary w-full"
                        disabled={submitting || !prompt}
                    >
                        Add to Queue
                    </button>

                    {#if queuedItems.length > 0}
                        <div class="mt-4 space-y-3">
                            <div
                                class="text-xs uppercase font-bold opacity-50 px-1"
                            >
                                Queued Batches ({queuedItems.length})
                            </div>
                            <div
                                class="max-h-60 overflow-y-auto space-y-2 pr-1"
                            >
                                {#each queuedItems as item (item.id)}
                                    <div
                                        class="bg-base-300 rounded-lg p-3 text-xs relative group border border-white/5"
                                    >
                                        <button
                                            onclick={() =>
                                                removeFromQueue(item.id)}
                                            class="absolute top-2 right-2 btn btn-ghost btn-xs btn-circle opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            ✕
                                        </button>
                                        <div class="font-bold truncate pr-6">
                                            {item.prompt}
                                        </div>
                                        <div class="opacity-60 mt-1 flex gap-2">
                                            <span>{item.modelTitle}</span>
                                            <span>•</span>
                                            <span class="text-primary"
                                                >{calculateJobCount(item)} jobs</span
                                            >
                                        </div>
                                    </div>
                                {/each}
                            </div>

                            <div class="divider"></div>

                            <button
                                type="button"
                                onclick={runExperiment}
                                class="btn btn-secondary w-full"
                                disabled={submitting}
                            >
                                {#if submitting}
                                    <span class="loading loading-spinner"
                                    ></span>
                                    Running {executionProgress.current}/{executionProgress.total}...
                                {:else}
                                    Start Full Experiment
                                {/if}
                            </button>

                            {#if submitting}
                                <progress
                                    class="progress progress-secondary w-full"
                                    value={executionProgress.current}
                                    max={executionProgress.total}
                                ></progress>
                            {/if}
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </form>
</div>
