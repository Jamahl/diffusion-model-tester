<script lang="ts">
    import { onMount } from "svelte";
    import { afterNavigate } from "$app/navigation";
    import { browser } from "$app/environment";

    type UseAgainChoice = "yes" | "no" | "test_more" | null;
type CurationStatus = "trash" | "use_again" | "top_1pct" | null;

interface ScoreBreakdown {
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
    curation_status: CurationStatus;
    flaws: string | string[] | null;
}

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
        scores: ScoreBreakdown;
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
    let ratingFilter = $state<"all" | "rated" | "unrated">("all");

    // Hover Preview State
    let hoveredRow = $state<Row | null>(null);
    let mousePos = $state({ x: 0, y: 0 });

    function handleMouseMove(e: MouseEvent) {
        mousePos = { x: e.clientX, y: e.clientY };
    }

    function normalizeScores(scores: any): ScoreBreakdown {
        return {
            score_overall: scores?.score_overall ?? scores?.overall ?? null,
            score_facial_detail_realism:
                scores?.score_facial_detail_realism ??
                scores?.facial_detail_realism ??
                null,
            score_body_proportions:
                scores?.score_body_proportions ?? scores?.body_proportions ?? null,
            score_complexity_artistry:
                scores?.score_complexity_artistry ??
                scores?.complexity_artistry ??
                null,
            score_composition_framing:
                scores?.score_composition_framing ??
                scores?.composition_framing ??
                null,
            score_lighting_color:
                scores?.score_lighting_color ?? scores?.lighting_color ?? null,
            score_resolution_clarity:
                scores?.score_resolution_clarity ??
                scores?.resolution_clarity ??
                null,
            score_style_consistency:
                scores?.score_style_consistency ??
                scores?.style_consistency ??
                null,
            score_prompt_adherence:
                scores?.score_prompt_adherence ??
                scores?.prompt_adherence ??
                null,
            score_artifacts: scores?.score_artifacts ?? scores?.artifacts ?? null,
            use_again: scores?.use_again ?? null,
            curation_status: scores?.curation_status ?? null,
            flaws: scores?.flaws ?? null,
        };
    }

    function averageSubScores(scores: ScoreBreakdown): number | null {
        const values = [
            scores.score_facial_detail_realism,
            scores.score_body_proportions,
            scores.score_complexity_artistry,
            scores.score_composition_framing,
            scores.score_lighting_color,
            scores.score_resolution_clarity,
            scores.score_style_consistency,
            scores.score_prompt_adherence,
            scores.score_artifacts,
        ]
            .map((v) => (v == null ? null : Number(v)))
            .filter((v): v is number => Number.isFinite(v));

        if (!values.length) return null;
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        return Number(avg.toFixed(1));
    }

    async function fetchData() {
        try {
            loading = true;
            const res = await fetch("http://localhost:8000/api/analysis/table");
            const data = await res.json();
            rows = Array.isArray(data)
                ? data.map((row) => ({
                      ...row,
                      scores: normalizeScores(row.scores),
                  }))
                : [];
        } catch (e) {
            console.error("Failed to fetch analysis data", e);
        } finally {
            loading = false;
        }
    }

    const filteredRows = $derived(
        rows
            .filter((r: Row) => {
                const matchesText =
                    r.prompt.toLowerCase().includes(search.toLowerCase()) ||
                    r.run_name.toLowerCase().includes(search.toLowerCase()) ||
                    r.model_id.toLowerCase().includes(search.toLowerCase()) ||
                    r.batch.toString().includes(search);
                const matchesRating =
                    ratingFilter === "all" ||
                    (ratingFilter === "rated" && r.image.is_rated) ||
                    (ratingFilter === "unrated" && !r.image.is_rated);
                return matchesText && matchesRating;
            })
            .sort((a: Row, b: Row) => {
                let valA: any;
                let valB: any;

                if (sortBy === "score") {
                    valA = a.scores.score_overall || 0;
                    valB = b.scores.score_overall || 0;
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

    function formatFlaws(flaws: string | string[] | null): string {
        if (!flaws) return "-";
        if (Array.isArray(flaws)) return flaws.join(", ");
        try {
            const parsed = JSON.parse(flaws);
            if (Array.isArray(parsed)) {
                return parsed.join(", ");
            }
        } catch {
            // treat as plain string
        }
        return flaws;
    }

    onMount(() => {
        fetchData();
        if (!browser) return;
        return afterNavigate(({ from }) => {
            if (from) {
                fetchData();
            }
        });
    });
</script>

<div class="flex flex-col h-full overflow-hidden font-mono bg-[#d4d0c8]">
    <!-- Window Header -->
    <div class="win95-title-bar shrink-0">
        <span class="flex items-center gap-2"
            ><span class="material-symbols-outlined text-[16px]">analytics</span
            > C:\EXPERIMENTS\ANALYSIS.EXE</span
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

    <!-- Toolbar -->
    <div
        class="p-4 border-b-2 border-white shadow-[0_1px_0_#808080] flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
    >
        <div>
            <h1
                class="text-2xl font-pixel uppercase tracking-wider text-black leading-none"
            >
                Cross-Run Analysis
            </h1>
            <p
                class="text-win-purple text-[10px] font-bold mt-1 tracking-tight italic"
            >
                &gt;_ Comparing parameter stacks and adherence metrics
            </p>
        </div>
        <div class="flex gap-2 w-full md:w-auto flex-wrap items-center">
            <div class="flex gap-1">
                <button
                    class="win95-btn h-8 px-3 text-[10px] font-bold uppercase {ratingFilter === 'all'
                        ? 'bg-win-purple text-white'
                        : 'bg-white text-black'}"
                    onclick={() => (ratingFilter = "all")}
                >
                    All
                </button>
                <button
                    class="win95-btn h-8 px-3 text-[10px] font-bold uppercase {ratingFilter === 'rated'
                        ? 'bg-win-purple text-white'
                        : 'bg-white text-black'}"
                    onclick={() => (ratingFilter = "rated")}
                >
                    Rated
                </button>
                <button
                    class="win95-btn h-8 px-3 text-[10px] font-bold uppercase {ratingFilter === 'unrated'
                        ? 'bg-win-purple text-white'
                        : 'bg-white text-black'}"
                    onclick={() => (ratingFilter = "unrated")}
                >
                    Unrated
                </button>
            </div>
            <div class="relative flex-1 md:flex-none">
                <input
                    type="text"
                    bind:value={search}
                    placeholder="Search stack..."
                    class="win95-input h-9 px-2 text-base w-full md:w-64"
                />
            </div>
            <a
                href="http://localhost:8000/api/analysis/csv"
                class="win95-btn h-9 px-4 text-xs font-bold uppercase flex items-center gap-2 no-underline text-black hover:bg-white"
                download
            >
                <span class="material-symbols-outlined text-[16px]"
                    >download</span
                > Export
            </a>
        </div>
    </div>

    <!-- Main Table Area -->
    <div class="flex-1 overflow-auto p-4 custom-scrollbar">
        {#if loading}
            <div class="h-full flex items-center justify-center">
                <span class="loading loading-spinner loading-lg text-primary"
                ></span>
            </div>
        {:else}
            <div class="win95-inset bg-white">
                <table class="table table-xs w-full text-left border-collapse">
                    <thead class="sticky top-0 z-20">
                        <tr
                            class="bg-gray-200 text-black text-[10px] uppercase font-bold border-b-2 border-black"
                        >
                            <th
                                class="p-2 border-r border-gray-400 cursor-pointer hover:bg-gray-300"
                                onclick={() => toggleSort("batch")}
                            >
                                Batch {sortBy === "batch"
                                    ? sortOrder === "asc"
                                        ? "↑"
                                        : "↓"
                                    : ""}
                            </th>
                            <th class="p-2 border-r border-gray-400">Preview</th
                            >
                            <th
                                class="p-2 border-r border-gray-400 cursor-pointer hover:bg-gray-300"
                                onclick={() => toggleSort("model_id")}
                            >
                                Model {sortBy === "model_id"
                                    ? sortOrder === "asc"
                                        ? "↑"
                                        : "↓"
                                    : ""}
                            </th>
                            <th class="p-2 border-r border-gray-400"
                                >Configuration</th
                            >
                            <th
                                class="p-2 border-r border-gray-400 text-center cursor-pointer hover:bg-gray-300"
                                onclick={() => toggleSort("score")}
                            >
                                Quality {sortBy === "score"
                                    ? sortOrder === "asc"
                                        ? "↑"
                                        : "↓"
                                    : ""}
                            </th>
                            <th class="p-2 border-r border-gray-400 text-center">
                                <span class="tooltip-trigger cursor-help">
                                    Avg Score
                                    <div class="tooltip-panel text-[9px] w-48">
                                        Average of all sub-scores (excluding overall).
                                    </div>
                                </span>
                            </th>
                            <th class="p-2 border-r border-gray-400 text-center"
                                >Curation</th
                            >
                            <th class="p-2 border-r border-gray-400"
                                >Flaws</th
                            >
                            <th class="p-2 border-r border-gray-400">Prompt</th>
                            <th class="p-2 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-300">
                        {#each filteredRows as row (row.id)}
                            <tr
                                class="hover:bg-win-magenta hover:text-white group"
                            >
                                <td
                                    class="p-2 font-pixel text-lg font-bold opacity-70 group-hover:opacity-100 group-hover:text-yellow-300"
                                    >#{row.batch}</td
                                >
                                <td class="p-2">
                                    <a
                                        href={`/runs/${row.run_id}/review/${row.id}`}
                                        class="block"
                                        onmouseenter={() => (hoveredRow = row)}
                                        onmouseleave={() => (hoveredRow = null)}
                                        onmousemove={handleMouseMove}
                                    >
                                        <div class="relative inline-block">
                                            {#if row.image.upscale_url}
                                                <span
                                                    class="absolute -top-2 -right-2 bg-yellow-300 text-[8px] font-bold uppercase px-1 py-0.5 border border-black shadow-[1px_1px_0_#000] group-hover:text-black"
                                                    title="Upscaled available"
                                                >
                                                    Upscaled
                                                </span>
                                            {/if}
                                            <div
                                                class="w-10 h-10 border border-black shadow-sm group-hover:border-white transition-transform group-hover:scale-110"
                                            >
                                                <img
                                                    src={getImageUrl(
                                                        row.image.file_path,
                                                    )}
                                                    alt="Result"
                                                    class="w-full h-full object-cover"
                                                />
                                            </div>
                                        </div>
                                    </a>
                                </td>
                                <td class="p-2">
                                    <div class="flex flex-col">
                                        <span
                                            class="text-[9px] uppercase font-bold opacity-40 group-hover:opacity-100"
                                            >{row.model_id}</span
                                        >
                                        <span
                                            class="text-[10px] font-bold truncate max-w-[80px] group-hover:text-yellow-200"
                                            >{row.run_name}</span
                                        >
                                    </div>
                                </td>
                                <td class="p-2">
                                    <div
                                        class="flex flex-wrap gap-1 max-w-[200px]"
                                    >
                                        <span
                                            class="px-1 border border-black bg-gray-100 text-[8px] font-bold group-hover:bg-black group-hover:text-white group-hover:border-white uppercase"
                                            >{row.config.steps} STEPS</span
                                        >
                                        <span
                                            class="px-1 border border-black bg-gray-100 text-[8px] font-bold group-hover:bg-black group-hover:text-white group-hover:border-white uppercase"
                                            >{row.config.scale} CFG</span
                                        >
                                        <span
                                            class="px-1 border border-black bg-gray-100 text-[8px] font-bold group-hover:bg-black group-hover:text-white group-hover:border-white uppercase italic"
                                            >{row.config.scheduler}</span
                                        >
                                        <span
                                            class="px-1 border border-black bg-gray-50 text-[8px] font-bold group-hover:bg-black group-hover:text-white group-hover:border-white"
                                            >{row.config.width}x{row.config
                                                .height}</span
                                        >
                                    </div>
                                </td>
                                <td class="p-2 text-center">
                                    {#if row.scores.score_overall}
                                        <span
                                            class="font-pixel text-xl font-bold group-hover:text-yellow-300"
                                            >{row.scores.score_overall}</span
                                        >
                                    {:else}
                                        <span class="opacity-20">-</span>
                                    {/if}
                                </td>
                                <td class="p-2 text-center text-[10px] font-bold">
                                    {#if averageSubScores(row.scores) !== null}
                                        <span class="font-pixel text-base group-hover:text-yellow-300">
                                            {averageSubScores(row.scores)}
                                        </span>
                                    {:else}
                                        <span class="opacity-20">-</span>
                                    {/if}
                                </td>
                                <td class="p-2 text-center">
                                    {#if row.scores.curation_status}
                                        <span
                                            class="text-[9px] font-bold uppercase px-1 border group-hover:border-white group-hover:text-black {row.scores
                                                .curation_status === 'trash'
                                                ? 'bg-red-600 text-white'
                                                : row.scores.curation_status ===
                                                      'use_again'
                                                  ? 'bg-blue-600 text-white'
                                                  : 'bg-yellow-400 text-black'}"
                                            >{row.scores.curation_status}</span
                                        >
                                    {:else}
                                        <span class="opacity-20">-</span>
                                    {/if}
                                </td>
                                <td class="p-2">
                                    <span
                                        class="text-[10px] uppercase tracking-tight opacity-60 group-hover:opacity-100"
                                        >{formatFlaws(row.scores.flaws)}</span
                                    >
                                </td>
                                <td class="p-2 max-w-xs">
                                    <p
                                        class="text-[10px] line-clamp-1 italic opacity-60 group-hover:opacity-100 group-hover:text-yellow-100"
                                    >
                                        "{row.prompt}"
                                    </p>
                                </td>
                                <td class="p-2 text-right">
                                    <a
                                        href={`/runs/${row.run_id}/review/${row.id}`}
                                        class="win95-btn px-2 py-0.5 text-[9px] font-bold uppercase no-underline text-black group-hover:bg-white group-hover:text-win-magenta"
                                    >
                                        Open
                                    </a>
                                </td>
                            </tr>
                        {:else}
                            <tr>
                                <td
                                    colspan="9"
                                    class="p-20 text-center opacity-40 italic font-pixel text-2xl tracking-widest bg-gray-50"
                                >
                                    QUERY_RESULT: NULL_SET
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>

    <!-- Hover Preview Portal -->
    {#if hoveredRow}
        <div
            class="fixed z-[100] pointer-events-none"
            style="left: {mousePos.x + 20}px; top: {Math.max(
                10,
                Math.min(600, mousePos.y - 150),
            )}px;"
        >
            <div
                class="win95-window p-1 shadow-2xl animate-in fade-in zoom-in duration-200 border-2 border-white shadow-[4px_4px_0_0_rgba(0,0,0,0.3)] bg-[#c0c0c0]"
            >
                <div
                    class="win95-title-bar py-1 px-3 flex justify-between items-center bg-win-blue"
                >
                    <span
                        class="text-[10px] uppercase font-bold text-white tracking-widest flex items-center gap-2"
                    >
                        <span class="material-symbols-outlined text-[14px]"
                            >image</span
                        >
                        DATA_PREVIEW: {hoveredRow.id.slice(0, 8)}.EXE
                    </span>
                </div>

                <div class="p-1 bg-[#808080] win95-inset border-2">
                    <img
                        src={getImageUrl(hoveredRow.image.file_path)}
                        alt="Preview"
                        class="max-w-[340px] max-h-[500px] object-contain block bg-checkered shadow-[inset_0_0_10px_rgba(0,0,0,0.5)]"
                    />
                </div>

                <div
                    class="bg-[#d4d0c8] p-3 border-t-2 border-white mt-1 shadow-[inset_1px_1px_0_#fff]"
                >
                    <div class="flex items-start gap-2 mb-2">
                        <span
                            class="material-symbols-outlined text-win-purple text-base"
                            >terminal</span
                        >
                        <p
                            class="text-[11px] font-bold text-black leading-tight italic break-words max-w-[300px]"
                        >
                            "{hoveredRow.prompt}"
                        </p>
                    </div>

                    <div
                        class="flex justify-between items-center py-1 border-t border-gray-400 mt-2"
                    >
                        <div class="flex flex-col">
                            <span
                                class="text-[8px] uppercase font-bold opacity-50"
                                >Cluster_ID</span
                            >
                            <span class="text-[10px] font-pixel text-win-blue"
                                >BATCH_00{hoveredRow.batch}</span
                            >
                        </div>
                        <div class="flex flex-col text-right">
                            <span
                                class="text-[8px] uppercase font-bold opacity-50"
                                >Logic_Engine</span
                            >
                            <span class="text-[10px] font-bold text-win-magenta"
                                >{hoveredRow.model_id}</span
                            >
                        </div>
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>
