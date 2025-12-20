<script lang="ts">
    import { onMount } from "svelte";

    interface Row {
        id: string;
        run_id: string;
        batch: number;
        run_name: string;
        created_at: string;
        prompt: string;
        model_id: string;
        config: {
            steps: number | null;
            scale: number | null;
            width: number | null;
            height: number | null;
            scheduler: string | null;
            seed: number | null;
            credit_cost: number;
        };
        scores: {
            overall_quality: number | null;
            anatomy_score: number | null;
            prompt_adherence: number | null;
            background_score: number | null;
            use_again: string | null;
        };
        image: {
            file_path: string | null;
            upscale_url: string | null;
            is_rated: boolean;
        };
    }

    let rows = $state<Row[]>([]);
    let loading = $state(true);
    let search = $state("");
    let sortBy = $state<keyof Row | "score">("batch");
    let sortOrder = $state<"asc" | "desc">("desc");

    async function fetchData() {
        try {
            loading = true;
            const res = await fetch("http://localhost:8000/api/analysis/table");
            rows = await res.json();
        } catch (e) {
            console.error("Failed to fetch analysis data", e);
        } finally {
            loading = false;
        }
    }

    const filteredRows = $derived(
        rows
            .filter(
                (r: Row) =>
                    r.prompt.toLowerCase().includes(search.toLowerCase()) ||
                    r.run_name.toLowerCase().includes(search.toLowerCase()) ||
                    r.model_id.toLowerCase().includes(search.toLowerCase()),
            )
            .sort((a: Row, b: Row) => {
                let valA: any;
                let valB: any;

                if (sortBy === "score") {
                    valA = a.scores.overall_quality || 0;
                    valB = b.scores.overall_quality || 0;
                } else {
                    valA = a[sortBy as keyof Row];
                    valB = b[sortBy as keyof Row];
                }

                if (valA < valB) return sortOrder === "asc" ? -1 : 1;
                if (valA > valB) return sortOrder === "asc" ? 1 : -1;
                return 0;
            }),
    );

    function toggleSort(key: keyof Row | "score") {
        if (sortBy === key) {
            sortOrder = sortOrder === "asc" ? "desc" : "asc";
        } else {
            sortBy = key;
            sortOrder = "desc";
        }
    }

    function getImageUrl(path: string | null) {
        if (!path) return "";
        if (path.startsWith("http")) return path;
        const filename = path.split("/").pop();
        return `http://localhost:8000/images/${filename}`;
    }

    onMount(fetchData);
</script>

<div class="flex flex-col gap-6 h-full">
    <div
        class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
    >
        <div>
            <h1 class="text-3xl font-bold">Cross-Run Analysis</h1>
            <p class="text-base-content/60">
                Compare parameters and scores across all experiment batches.
            </p>
        </div>
        <div class="flex gap-2 w-full md:w-auto">
            <input
                type="text"
                bind:value={search}
                placeholder="Search prompts, runs..."
                class="input input-bordered w-full md:w-64"
            />
            <a
                href="http://localhost:8000/api/analysis/csv"
                class="btn btn-primary"
                download
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                    />
                </svg>
                Export CSV
            </a>
        </div>
    </div>

    {#if loading}
        <div class="flex-1 flex items-center justify-center">
            <span class="loading loading-spinner loading-lg text-primary"
            ></span>
        </div>
    {:else}
        <div
            class="card bg-base-200 shadow-xl overflow-hidden border border-white/5"
        >
            <div class="overflow-x-auto">
                <table class="table table-sm table-pin-rows">
                    <thead>
                        <tr class="bg-base-300">
                            <th
                                class="cursor-pointer hover:bg-base-100"
                                onclick={() => toggleSort("batch")}
                            >
                                Batch {sortBy === "batch"
                                    ? sortOrder === "asc"
                                        ? "↑"
                                        : "↓"
                                    : ""}
                            </th>
                            <th>Image</th>
                            <th
                                class="cursor-pointer hover:bg-base-100"
                                onclick={() => toggleSort("model_id")}
                            >
                                Model {sortBy === "model_id"
                                    ? sortOrder === "asc"
                                        ? "↑"
                                        : "↓"
                                    : ""}
                            </th>
                            <th class="max-w-xs">Config</th>
                            <th
                                class="cursor-pointer hover:bg-base-100 text-center"
                                onclick={() => toggleSort("score")}
                            >
                                Quality {sortBy === "score"
                                    ? sortOrder === "asc"
                                        ? "↑"
                                        : "↓"
                                    : ""}
                            </th>
                            <th class="text-center">Scores (A/P/B)</th>
                            <th class="text-center">Prod</th>
                            <th>Prompt</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each filteredRows as row: Row (row.id)}
                            <tr class="hover group">
                                <td class="font-mono font-bold opacity-50"
                                    >#{row.batch}</td
                                >
                                <td>
                                    <div class="avatar">
                                        <div
                                            class="w-12 h-12 rounded-lg ring-1 ring-white/10 group-hover:ring-primary transition-all"
                                        >
                                            <img
                                                src={getImageUrl(
                                                    row.image.file_path,
                                                )}
                                                alt="Result"
                                            />
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <div class="flex flex-col">
                                        <span
                                            class="text-[10px] uppercase font-bold opacity-40"
                                            >{row.model_id}</span
                                        >
                                        <span
                                            class="text-xs font-semibold truncate max-w-[100px]"
                                            >{row.run_name}</span
                                        >
                                    </div>
                                </td>
                                <td>
                                    <div class="flex flex-wrap gap-1">
                                        <span
                                            class="badge badge-outline badge-xs opacity-60"
                                            >{row.config.steps} steps</span
                                        >
                                        <span
                                            class="badge badge-outline badge-xs opacity-60"
                                            >{row.config.scale} cfg</span
                                        >
                                        <span
                                            class="badge badge-outline badge-xs opacity-60 uppercase"
                                            >{row.config.scheduler}</span
                                        >
                                    </div>
                                </td>
                                <td class="text-center">
                                    {#if row.scores.overall_quality}
                                        <div
                                            class="badge badge-primary font-bold"
                                        >
                                            {row.scores.overall_quality}
                                        </div>
                                    {:else}
                                        <div
                                            class="badge badge-ghost opacity-20"
                                        >
                                            -
                                        </div>
                                    {/if}
                                </td>
                                <td class="text-center">
                                    <div
                                        class="flex gap-1 justify-center opacity-70"
                                    >
                                        <span class="tooltip" data-tip="Anatomy"
                                            >{row.scores.anatomy_score ||
                                                "-"}</span
                                        >
                                        <span>/</span>
                                        <span
                                            class="tooltip"
                                            data-tip="Prompt Adherence"
                                            >{row.scores.prompt_adherence ||
                                                "-"}</span
                                        >
                                        <span>/</span>
                                        <span
                                            class="tooltip"
                                            data-tip="Background"
                                            >{row.scores.background_score ||
                                                "-"}</span
                                        >
                                    </div>
                                </td>
                                <td class="text-center">
                                    {#if row.scores.use_again === "yes"}
                                        <div
                                            class="badge badge-success badge-xs"
                                        >
                                            YES
                                        </div>
                                    {:else if row.scores.use_again === "no"}
                                        <div class="badge badge-error badge-xs">
                                            NO
                                        </div>
                                    {:else if row.scores.use_again === "test_more"}
                                        <div
                                            class="badge badge-warning badge-xs"
                                        >
                                            MAYBE
                                        </div>
                                    {:else}
                                        <span class="opacity-20">-</span>
                                    {/if}
                                </td>
                                <td class="max-w-xs">
                                    <p
                                        class="text-[10px] line-clamp-2 opacity-60 italic leading-tight"
                                    >
                                        "{row.prompt}"
                                    </p>
                                </td>
                                <td>
                                    <a
                                        href="/runs/{row.run_id}/review/{row.id}"
                                        class="btn btn-ghost btn-xs"
                                    >
                                        View
                                    </a>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}
</div>
