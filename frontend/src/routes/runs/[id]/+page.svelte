<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/state";

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
    }

    interface Image {
        id: string;
        file_path: string | null;
        overall_quality: number | null;
        is_rated: boolean;
    }

    let run = $state<Run | null>(null);
    let images = $state<Image[]>([]);
    let unratedOnly = $state(false);
    let loading = $state(true);
    let error = $state<string | null>(null);

    async function fetchRunDetail() {
        try {
            const res = await fetch(
                `http://localhost:8000/api/runs/${page.params.id}`,
            );
            if (!res.ok) throw new Error("Run not found");
            run = await res.json();
        } catch (e: any) {
            error = e.message;
        }
    }

    async function fetchImages() {
        try {
            loading = true;
            const url = new URL(`http://localhost:8000/api/images`);
            url.searchParams.set("run_id", page.params.id);
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

    function getImageUrl(path: string | null) {
        if (!path) return "/placeholder.png";
        // path is local like 'storage/images/uuid.png'
        // We serve images from /images mount in FastAPI
        const filename = path.split("/").pop();
        return `http://localhost:8000/images/${filename}`;
    }

    $effect(() => {
        // Re-fetch images when filter changes
        fetchImages();
    });

    onMount(async () => {
        await fetchRunDetail();
        await fetchImages();
    });
</script>

<div class="flex flex-col gap-8 h-full">
    {#if error}
        <div class="alert alert-error">{error}</div>
    {:else if run}
        <!-- Run Header -->
        <div
            class="flex flex-col md:flex-row gap-6 items-start justify-between"
        >
            <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                    <span
                        class="badge badge-lg badge-neutral font-mono font-bold"
                        >#{run.batch_number}</span
                    >
                    <h1 class="text-3xl font-bold">{run.name}</h1>
                </div>
                <p class="text-base-content/70 italic line-clamp-2">
                    "{run.prompt}"
                </p>
                <div class="flex gap-4 mt-2 text-xs opacity-50">
                    <span>Model: {run.model_id}</span>
                    <span>Total: {run.counts.total_images}</span>
                    <span>Unrated: {run.counts.unrated}</span>
                </div>
            </div>

            <div class="flex flex-col gap-3 w-full md:w-auto">
                <div
                    class="form-control bg-base-200 p-3 rounded-lg border border-base-300"
                >
                    <label class="label cursor-pointer gap-4">
                        <span class="label-text font-semibold"
                            >Unrated Only</span
                        >
                        <input
                            type="checkbox"
                            bind:checked={unratedOnly}
                            class="toggle toggle-primary"
                        />
                    </label>
                </div>
                <a href="/jobs" class="btn btn-outline btn-sm"
                    >View Work Queue</a
                >
            </div>
        </div>

        <!-- Image Gallery -->
        {#if loading}
            <div class="flex-1 flex justify-center py-20">
                <span class="loading loading-spinner loading-lg text-primary"
                ></span>
            </div>
        {:else if images.length === 0}
            <div
                class="flex-1 card bg-base-200 border-2 border-dashed border-base-300 py-32 items-center text-center"
            >
                <h2 class="text-xl font-bold opacity-30">
                    {unratedOnly
                        ? "No unrated images left!"
                        : "No images generated yet."}
                </h2>
                <p class="opacity-20">
                    If this run was just created, check the Queue to start
                    processing.
                </p>
            </div>
        {:else}
            <div
                class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4"
            >
                {#each images as image}
                    <a
                        href="/runs/{run.id}/review/{image.id}"
                        class="group relative aspect-[512/768] bg-base-300 rounded-xl overflow-hidden shadow-lg hover:ring-4 hover:ring-primary transition-all duration-300"
                    >
                        <img
                            src={getImageUrl(image.file_path)}
                            alt="Generated result"
                            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                            loading="lazy"
                        />

                        {#if image.overall_quality}
                            <div
                                class="absolute top-2 right-2 badge badge-primary font-bold shadow-lg"
                            >
                                {image.overall_quality}
                            </div>
                        {:else}
                            <div
                                class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity"
                            >
                                <span class="badge badge-outline text-white"
                                    >Unrated</span
                                >
                            </div>
                        {/if}

                        <div
                            class="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                            <span
                                class="text-xs text-white uppercase font-bold tracking-wider"
                                >Click to Review</span
                            >
                        </div>
                    </a>
                {/each}
            </div>
        {/if}
    {:else}
        <div class="flex justify-center py-20">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {/if}
</div>
