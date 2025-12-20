<script lang="ts">
    import { onMount } from "svelte";
    import { toasts } from "$lib/stores/toasts";

    type CurationStatus = "trash" | "keep" | "showcase";
    type RLHFField = "score_fidelity" | "score_alignment" | "score_aesthetics";

    interface Image {
        id: string;
        run_id: string;
        file_path: string | null;
        overall_quality: number | null;
        is_rated: boolean;
        score_fidelity?: number | null;
        score_alignment?: number | null;
        score_aesthetics?: number | null;
        curation_status?: CurationStatus | null;
        flaws?: string | string[] | null;
    }

    let images = $state<Image[]>([]);
    let loading = $state(true);
    let total = $state(0);
    let offset = $state(0);
    let flawDrafts = $state<Record<string, string>>({});
    const limit = 20;

    const rlhfControls: { key: RLHFField; label: string; accent: string }[] = [
        { key: "score_fidelity", label: "Fidelity", accent: "text-blue-700" },
        { key: "score_alignment", label: "Alignment", accent: "text-win-purple" },
        { key: "score_aesthetics", label: "Aesthetics", accent: "text-pink-600" },
    ];

    async function fetchUnratedImages() {
        try {
            loading = true;
            const res = await fetch(
                `http://localhost:8000/api/images?unrated_only=true&limit=${limit}&offset=${offset}`,
            );
            const data = await res.json();
            images = data.images;
            total = data.total;
            flawDrafts = {};
        } catch (e) {
            console.error("Failed to fetch unrated images", e);
            toasts.error("Failed to load unrated images");
        } finally {
            loading = false;
        }
    }

    function formatFlawString(raw?: string | string[] | null): string {
        if (!raw) return "";
        if (Array.isArray(raw)) {
            return raw.join(", ");
        }
        try {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) {
                return parsed.join(", ");
            }
        } catch {
            // Ignore JSON parse errors; treat as plain string
        }
        return raw;
    }

    function getFlawDraft(image: Image) {
        return flawDrafts[image.id] ?? formatFlawString(image.flaws);
    }

    function handleFlawInput(imageId: string, value: string) {
        flawDrafts = { ...flawDrafts, [imageId]: value };
    }

    function saveFlaws(image: Image) {
        const raw = (flawDrafts[image.id] ?? formatFlawString(image.flaws)).trim();
        const tags = raw
            ? raw
                  .split(",")
                  .map((entry) => entry.trim())
                  .filter(Boolean)
            : [];
        updateScore(image.id, { flaws: tags });
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
                        ? {
                              ...img,
                              ...data.scores,
                              is_rated:
                                  data.scores.overall_quality != null
                                      ? true
                                      : img.is_rated,
                          }
                        : img,
                );
                if (data.scores?.flaws !== undefined) {
                    flawDrafts = {
                        ...flawDrafts,
                        [imageId]: formatFlawString(data.scores.flaws),
                    };
                }
                // If it was the final rating (overall_quality set), we might want to hide it
                if (payload.overall_quality) {
                    setTimeout(() => {
                        images = images.filter((img) => img.id !== imageId);
                        const { [imageId]: _discard, ...rest } = flawDrafts;
                        flawDrafts = rest;
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
                                class="w-1/2 flex flex-col gap-3 p-1 bg-[#d4d0c8] win95-inset overflow-y-auto scrollbar-hide"
                            >
                                <!-- Overall Quality 1-10 -->
                                <div class="flex flex-col gap-1">
                                    <div
                                        class="flex justify-between items-center text-[8px] font-bold uppercase text-win-purple"
                                    >
                                        <span>Quality (1-10)</span>
                                        <span class="text-black">{image.overall_quality || "-"}</span>
                                    </div>
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

                                <!-- RLHF Vector -->
                                <div
                                    class="border-t border-gray-400 pt-2 mt-1 space-y-2"
                                >
                                    <div class="text-[8px] font-bold uppercase text-gray-600">
                                        RLHF Vector (1-5)
                                    </div>
                                    <div class="space-y-2">
                                        {#each rlhfControls as control}
                                            <div class="flex flex-col gap-1">
                                                <div
                                                    class="flex justify-between text-[8px] font-bold uppercase"
                                                >
                                                    <span class={control.accent}>
                                                        {control.label}
                                                    </span>
                                                    <span class="text-black"
                                                        >{image[control.key] || "-"}</span
                                                    >
                                                </div>
                                                <input
                                                    type="range"
                                                    min="1"
                                                    max="5"
                                                    step="1"
                                                    value={image[control.key] || 3}
                                                    onchange={(e) =>
                                                        updateScore(image.id, {
                                                            [control.key]: parseInt(
                                                                e.currentTarget.value,
                                                            ),
                                                        })}
                                                    class="range-retro-small"
                                                />
                                            </div>
                                        {/each}
                                    </div>
                                </div>

                                <!-- Curation + Flaws -->
                                <div class="mt-auto space-y-2">
                                    <div class="flex flex-col gap-1">
                                        <span
                                            class="text-[8px] font-bold uppercase text-gray-600"
                                            >Curation</span
                                        >
                                        <div class="flex gap-1 justify-center">
                                            {#each [
                                                { value: "trash", icon: "delete", color: "bg-red-600" },
                                                { value: "keep", icon: "save", color: "bg-blue-600" },
                                                {
                                                    value: "showcase",
                                                    icon: "star",
                                                    color: "bg-yellow-400",
                                                },
                                            ] as action}
                                                <button
                                                    onclick={() =>
                                                        updateScore(image.id, {
                                                            curation_status: action.value,
                                                        })}
                                                    class="p-1 aspect-square flex items-center justify-center border border-white {image.curation_status ===
                                                    action.value
                                                        ? `${action.color} text-white`
                                                        : 'bg-[#c0c0c0] hover:bg-white'}"
                                                    title={action.value}
                                                >
                                                    <span
                                                        class="material-symbols-outlined text-[14px]"
                                                        >{action.icon}</span
                                                    >
                                                </button>
                                            {/each}
                                        </div>
                                    </div>

                                    <div class="flex flex-col gap-1">
                                        <span
                                            class="text-[8px] font-bold uppercase text-gray-600"
                                            >Flaw Tags (comma separated)</span
                                        >
                                        <div class="flex gap-1">
                                            <input
                                                type="text"
                                                value={getFlawDraft(image)}
                                                oninput={(e) =>
                                                    handleFlawInput(
                                                        image.id,
                                                        e.currentTarget.value,
                                                    )}
                                                class="flex-1 win95-input h-7 px-2 text-[10px]"
                                                placeholder="hands, eyes, background"
                                            />
                                            <button
                                                onclick={() => saveFlaws(image)}
                                                class="win95-btn px-2 text-[9px] font-bold uppercase"
                                            >
                                                Save
                                            </button>
                                        </div>
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
