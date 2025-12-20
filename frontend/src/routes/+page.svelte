<script lang="ts">
	import { onMount, onDestroy } from "svelte";
	import { toasts } from "$lib/stores/toasts";

	interface Run {
		id: string;
		batch_number: number;
		name: string;
		created_at: string;
		prompt: string;
		model_id: string;
		total_images: number;
		unrated_count: number;
		upscaled_count: number;
		queued_jobs: number;
		total_cost: number;
	}

	interface Job {
		id: number;
		run_id: string;
		status: string;
		run_name: string;
		run_batch: number;
		config: any;
	}

	let runs = $state<Run[]>([]);
	let queuedJobs = $state<Job[]>([]);
	let loading = $state(true);
	let processingJob = $state(false);
	let processingAll = $state(false);
	let error = $state<string | null>(null);
	let logs = $state<string[]>([
		"[OK] System v1.2.0-PATCH initialized.",
		"[OK] DB connection stable.",
		"[INFO] SinkIn Worker ready.",
	]);
	let pollInterval: any;
	let systemOnline = $state(true);

	async function checkSystemHealth() {
		try {
			const res = await fetch("http://localhost:8000/api/health");
			if (!res.ok) throw new Error("Health check failed");
			if (!systemOnline) {
				systemOnline = true;
				addLog("[SUCCESS] System connection restored.");
			}
		} catch (e) {
			if (systemOnline) {
				systemOnline = false;
				addLog("[CRITICAL] Verify API Connection. System offline.");
				addLog("[ERROR] Database/Backend unavailable.");
			}
		}
	}

	function addLog(msg: string) {
		const time = new Date().toLocaleTimeString([], {
			hour12: false,
			hour: "2-digit",
			minute: "2-digit",
			second: "2-digit",
		});
		logs = [...logs.slice(-50), `[${time}] ${msg}`];
	}

	// Computed Stats
	const totalImages = $derived(
		runs.reduce((acc, r) => acc + r.total_images, 0),
	);
	const successfulBatches = $derived(
		runs.filter((r) => r.total_images > 0).length,
	);
	const totalCost = $derived(runs.reduce((acc, r) => acc + r.total_cost, 0));
	const unratedTotal = $derived(
		runs.reduce((acc, r) => acc + r.unrated_count, 0),
	);

	async function fetchRuns() {
		try {
			const res = await fetch("http://localhost:8000/api/runs");
			if (!res.ok) throw new Error("Failed to fetch runs");
			const data = await res.json();
			runs = data.runs;
		} catch (e: any) {
			error = e.message;
		}
	}

	async function fetchQueue() {
		try {
			const res = await fetch(
				"http://localhost:8000/api/jobs?status=queued",
			);
			if (!res.ok) throw new Error("Failed to fetch queue");
			queuedJobs = await res.json();
		} catch (e: any) {
			console.error("Queue fetch error:", e);
		}
	}

	async function runNextJob(isAll = false) {
		if (queuedJobs.length === 0) {
			if (isAll) {
				processingAll = false;
				addLog("Queue empty. Stopping worker.");
			}
			return;
		}
		if (processingJob) return;

		processingJob = true;
		if (isAll) processingAll = true;

		try {
			addLog("Fetching next job from stack...");
			const nextRes = await fetch("http://localhost:8000/api/jobs/next");
			const { job_id } = await nextRes.json();

			if (!job_id) {
				addLog("[WARN] No jobs found in active queue.");
				processingAll = false;
				return;
			}

			addLog(`Starting job ID: ${job_id}`);
			const res = await fetch("http://localhost:8000/api/jobs/run", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ job_id }),
			});

			if (!res.ok) throw new Error("Failed to run job");

			addLog(`[SUCCESS] Job ${job_id} completed.`);
			await Promise.all([fetchRuns(), fetchQueue()]);

			if (isAll && queuedJobs.length > 0) {
				processingJob = false;
				setTimeout(() => runNextJob(true), 100);
			}
		} catch (e: any) {
			addLog(`[ERROR] ${e.message}`);
			toasts.error("Error running job: " + e.message);
			processingAll = false;
		} finally {
			processingJob = false;
		}
	}

	async function cancelAll() {
		if (!confirm("Are you sure you want to cancel all queued jobs?"))
			return;
		try {
			const res = await fetch(
				"http://localhost:8000/api/jobs/cancel-all",
				{ method: "POST" },
			);
			if (!res.ok) throw new Error("Failed to cancel jobs");
			toasts.info("All queued jobs cancelled");
			await Promise.all([fetchRuns(), fetchQueue()]);
		} catch (e: any) {
			toasts.error(e.message);
		}
	}

	async function cancelJob(jobId: number) {
		try {
			const res = await fetch(`http://localhost:8000/api/jobs/${jobId}`, {
				method: "DELETE",
			});
			if (!res.ok) throw new Error("Failed to cancel job");
			toasts.info("Job cancelled");
			await Promise.all([fetchRuns(), fetchQueue()]);
		} catch (e: any) {
			toasts.error(e.message);
		}
	}

	function formatDate(dateStr: string) {
		const date = new Date(dateStr);
		return (
			date.toLocaleDateString() +
			" " +
			date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
		);
	}

	onMount(async () => {
		loading = true;
		await Promise.all([fetchRuns(), fetchQueue()]);
		loading = false;

		pollInterval = setInterval(() => {
			fetchRuns();
			fetchQueue();
			checkSystemHealth();
		}, 5000);
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});
</script>

<div class="flex h-full overflow-hidden font-mono bg-[#d4d0c8]">
	<!-- Main View -->
	<div
		class="flex-1 flex flex-col h-full overflow-hidden border-r-2 border-white"
	>
		<!-- Window Header -->
		<div class="win95-title-bar shrink-0">
			<span class="flex items-center gap-2"
				><span class="material-symbols-outlined text-[16px]"
					>terminal</span
				> C:\EXPERIMENTS\DASHBOARD.EXE</span
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

		<!-- Scrollable Area -->
		<div class="flex-1 overflow-y-auto p-6 custom-scrollbar">
			<div class="max-w-[1200px] mx-auto flex flex-col gap-6">
				<!-- Header section -->
				<div
					class="flex flex-wrap justify-between items-end gap-4 border-b-2 border-gray-400 pb-4 shadow-[0_1px_0_#fff]"
				>
					<div class="flex flex-col gap-1">
						<h1
							class="text-black text-4xl font-pixel tracking-[0.1em] uppercase drop-shadow-[2px_2px_0_rgba(255,255,255,1)] leading-none"
						>
							Experiment Dashboard
						</h1>
						<p
							class="text-win-purple text-sm font-bold tracking-wide italic mt-1"
						>
							&gt;_ Monitoring generation history & active
							sequences
						</p>
					</div>
					<div class="flex gap-3">
						<a
							href="/analysis"
							class="flex items-center gap-2 h-9 px-4 win95-btn text-xs font-bold uppercase hover:bg-white transition-none no-underline text-black"
						>
							<span class="material-symbols-outlined text-[16px]"
								>analytics</span
							> Analysis
						</a>
						<a
							href="http://localhost:8000/api/analysis/csv"
							class="flex items-center gap-2 h-9 px-4 win95-btn text-xs font-bold uppercase hover:bg-white transition-none no-underline text-black"
							download
						>
							<span class="material-symbols-outlined text-[16px]"
								>save_alt</span
							> Export CSV
						</a>
					</div>
				</div>

				<!-- Stats Grid -->
				<div
					class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
				>
					<div
						class="flex flex-col gap-1 p-1 win95-inset bg-white shadow-retro-flat cursor-default"
					>
						<div
							class="bg-blue-800 text-white px-2 py-1 text-[10px] font-bold uppercase flex justify-between items-center"
						>
							<span class="tracking-wider">Total Images</span>
							<span class="material-symbols-outlined text-[14px]"
								>image</span
							>
						</div>
						<div class="p-3 text-center">
							<p class="text-black font-pixel text-4xl">
								{totalImages.toLocaleString()}
							</p>
						</div>
					</div>
					<div
						class="flex flex-col gap-1 p-1 win95-inset bg-white shadow-retro-flat cursor-default"
					>
						<div
							class="bg-purple-700 text-white px-2 py-1 text-[10px] font-bold uppercase flex justify-between items-center"
						>
							<span class="tracking-wider">Total Batches</span>
							<span class="material-symbols-outlined text-[14px]"
								>checklist</span
							>
						</div>
						<div class="p-3 text-center">
							<p class="text-black font-pixel text-4xl">
								{successfulBatches}
							</p>
						</div>
					</div>
					<div
						class="flex flex-col gap-1 p-1 win95-inset bg-white shadow-retro-flat cursor-default"
					>
						<div
							class="bg-pink-600 text-white px-2 py-1 text-[10px] font-bold uppercase flex justify-between items-center"
						>
							<span class="tracking-wider">Unrated</span>
							<span class="material-symbols-outlined text-[14px]"
								>pending_actions</span
							>
						</div>
						<div class="p-3 text-center">
							<p class="text-black font-pixel text-4xl">
								{unratedTotal}
							</p>
						</div>
					</div>
					<div
						class="flex flex-col gap-1 p-1 win95-inset bg-white shadow-retro-flat cursor-default"
					>
						<div
							class="bg-teal-700 text-white px-2 py-1 text-[10px] font-bold uppercase flex justify-between items-center"
						>
							<span class="tracking-wider">Credit Cost</span>
							<span class="material-symbols-outlined text-[14px]"
								>payments</span
							>
						</div>
						<div class="p-3 text-center">
							<p class="text-black font-pixel text-4xl">
								{totalCost.toFixed(1)}
							</p>
						</div>
					</div>
				</div>

				<!-- Batches Table -->
				<div
					class="flex flex-col gap-2 border-2 border-white border-b-[#404040] border-r-[#404040] p-4 bg-[#d4d0c8] shadow-[2px_2px_0_0_rgba(0,0,0,0.2)]"
				>
					<div class="flex items-center justify-between pb-2">
						<h2
							class="text-xl font-bold text-black uppercase font-pixel flex items-center gap-2"
						>
							<span
								class="w-3 h-3 bg-win-magenta inline-block border border-black shadow-[1px_1px_0_0_#000]"
							></span> Recent Batches
						</h2>
					</div>

					<div
						class="w-full overflow-x-auto bg-white win95-inset custom-scrollbar"
					>
						<table class="w-full text-left border-collapse">
							<thead>
								<tr
									class="bg-gray-200 text-black text-[10px] uppercase font-bold border-b-2 border-black"
								>
									<th
										class="p-3 border-r border-gray-400 tracking-wider"
										>Batch</th
									>
									<th
										class="p-3 border-r border-gray-400 tracking-wider"
										>Parameters</th
									>
									<th
										class="p-3 border-r border-gray-400 tracking-wider text-center"
										>Images</th
									>
									<th
										class="p-3 border-r border-gray-400 tracking-wider text-center"
										>Upscales</th
									>
									<th
										class="p-3 border-r border-gray-400 tracking-wider text-center"
										>Status</th
									>
									<th class="p-3 text-right tracking-wider"
										>Actions</th
									>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-400 bg-white">
								{#each runs as run}
									<tr
										class="group hover:bg-win-magenta hover:text-white transition-none cursor-default"
									>
										<td class="p-3 align-top">
											<span
												class="font-pixel text-xl font-bold group-hover:text-yellow-300"
												>#{run.batch_number}</span
											>
											<div
												class="text-[9px] uppercase mt-1 group-hover:text-white font-mono opacity-60 italic"
											>
												{formatDate(run.created_at)}
											</div>
										</td>
										<td class="p-3 align-top">
											<p
												class="text-xs font-bold truncate max-w-[240px] font-mono group-hover:text-white"
											>
												{run.name || "Untitled Run"}
											</p>
											<div
												class="flex items-center gap-2 mt-1"
											>
												<span
													class="text-[9px] px-1 bg-gray-100 text-black border border-black uppercase font-bold group-hover:bg-black group-hover:text-white group-hover:border-white"
													>{run.model_id}</span
												>
												<span
													class="text-[9px] uppercase font-bold opacity-60 group-hover:opacity-100 group-hover:text-yellow-200 truncate max-w-[150px] italic"
													>"{run.prompt}"</span
												>
											</div>
										</td>
										<td class="p-3 align-top text-center">
											<div
												class="text-sm font-bold font-pixel"
											>
												{run.total_images -
													run.unrated_count}/{run.total_images}
											</div>
											<div
												class="text-[9px] uppercase font-bold opacity-60 group-hover:text-white"
											>
												Rated
											</div>
										</td>
										<td class="p-3 align-top text-center">
											<div
												class="text-sm font-bold font-pixel"
											>
												{run.upscaled_count}
											</div>
											<div
												class="text-[9px] uppercase font-bold opacity-60 group-hover:text-white"
											>
												Total
											</div>
										</td>
										<td class="p-3 align-top text-center">
											{#if run.queued_jobs > 0}
												<div
													class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-yellow-100 border border-yellow-700 text-yellow-700 text-[10px] font-bold uppercase shadow-[1px_1px_0_0_rgba(0,0,0,0.2)]"
												>
													<span
														class="loading loading-spinner h-2 w-2"
													></span>
													{run.queued_jobs} Q
												</div>
											{:else if run.unrated_count === 0 && run.total_images > 0}
												<div
													class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-green-100 border border-green-700 text-green-700 text-[10px] font-bold uppercase shadow-[1px_1px_0_0_rgba(0,0,0,0.2)]"
												>
													<span
														class="material-symbols-outlined text-[12px]"
														>check</span
													> DONE
												</div>
											{:else}
												<div
													class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-blue-100 border border-blue-700 text-blue-700 text-[10px] font-bold uppercase shadow-[1px_1px_0_0_rgba(0,0,0,0.2)]"
												>
													READY
												</div>
											{/if}
										</td>
										<td class="p-3 text-right align-top">
											<a
												href="/runs/{run.id}"
												class="win95-btn px-3 py-1 text-[10px] font-bold uppercase no-underline text-black group-hover:bg-white group-hover:text-win-magenta"
											>
												Review
											</a>
										</td>
									</tr>
								{:else}
									<tr>
										<td
											colspan="6"
											class="p-20 text-center italic opacity-40"
											>No batches found. Create your first
											run!</td
										>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Queue Sidebar -->
	<div class="w-[320px] h-full flex flex-col shrink-0 bg-[#d4d0c8]">
		<div class="win95-title-bar shrink-0">
			<span>QUEUE_MGR</span>
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

		<div class="p-3 border-b border-white shadow-[0_1px_0_#808080]">
			<h3
				class="text-black text-xs font-bold uppercase flex items-center gap-2 tracking-wider"
			>
				<span
					class="material-symbols-outlined text-[18px] text-win-purple"
					>layers</span
				>
				Process Queue
			</h3>
		</div>

		<div
			class="flex-1 overflow-y-auto p-4 flex flex-col gap-6 custom-scrollbar"
		>
			<!-- Active Area -->
			<div class="flex flex-col gap-2">
				<div class="flex justify-between items-center mb-1">
					<h4
						class="text-black text-[10px] font-bold uppercase tracking-wider bg-white px-2 py-0.5 border border-gray-400 shadow-[2px_2px_0_0_rgba(0,0,0,0.1)]"
					>
						ACTIVE_SEQ
					</h4>
					{#if processingJob}
						<div
							class="w-3 h-3 bg-green-500 border border-black animate-pulse shadow-[1px_1px_0_rgba(0,0,0,1)]"
						></div>
					{/if}
				</div>

				<div
					class="p-3 win95-inset bg-gray-50 flex flex-col gap-3 group transition-colors"
				>
					{#if processingJob}
						<div class="flex flex-col gap-2">
							<div class="flex items-start justify-between">
								<div class="flex flex-col">
									<p
										class="text-black text-sm font-bold leading-tight uppercase font-pixel tracking-wide"
									>
										Inference Active
									</p>
									<p
										class="text-gray-600 text-[10px] font-mono mt-1 italic"
									>
										Processing next unit...
									</p>
								</div>
							</div>
							<div
								class="h-6 w-full bg-white border border-gray-600 relative p-[2px]"
							>
								<div
									class="h-full bg-gradient-to-r from-win-purple to-win-magenta animate-pulse"
									style="width: 100%"
								>
									<div
										class="w-full h-full"
										style="background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(255,255,255,0.2) 5px, rgba(255,255,255,0.2) 10px);"
									></div>
								</div>
							</div>
						</div>
					{:else if queuedJobs.length > 0}
						<div class="flex flex-col gap-3">
							<p
								class="text-black text-[10px] font-bold text-center italic opacity-60"
							>
								Ready to initiate workers...
							</p>
							<div class="grid grid-cols-2 gap-2">
								<button
									onclick={() => runNextJob(false)}
									disabled={processingJob || processingAll}
									class="win95-btn h-10 bg-white text-black uppercase font-bold text-[10px] flex items-center justify-center gap-1"
								>
									<span
										class="material-symbols-outlined text-[16px]"
										>play_arrow</span
									>
									Run One
								</button>
								<button
									onclick={() => runNextJob(true)}
									disabled={processingJob || processingAll}
									class="win95-btn h-10 bg-win-purple text-white uppercase font-bold text-[10px] flex items-center justify-center gap-1"
								>
									<span
										class="material-symbols-outlined text-[16px]"
										>dynamic_feed</span
									>
									Run All
								</button>
							</div>
						</div>
					{:else}
						<p
							class="text-[10px] text-center italic opacity-40 font-bold py-4"
						>
							No remaining jobs in global stack.
						</p>
					{/if}
				</div>
			</div>

			<!-- List Area -->
			<div class="flex flex-col gap-2">
				<div
					class="flex justify-between items-center border-b border-gray-400 pb-1 mb-2"
				>
					<h4
						class="text-black text-[10px] font-bold uppercase tracking-wider"
					>
						UPCOMING ({queuedJobs.length})
					</h4>
					{#if queuedJobs.length > 0}
						<button
							onclick={cancelAll}
							class="text-[9px] text-red-700 hover:text-red-500 font-bold uppercase underline"
							>Clear Stack</button
						>
					{/if}
				</div>

				<div class="flex flex-col gap-2">
					{#each queuedJobs.slice(0, 5) as job}
						<div
							class="p-2 border border-white border-b-black border-r-black bg-white shadow-[1px_1px_0_0_rgba(0,0,0,0.5)] cursor-default group"
						>
							<div class="flex justify-between items-start gap-2">
								<div class="flex gap-2 items-center min-w-0">
									<span
										class="material-symbols-outlined text-win-purple text-[16px]"
										>hourglass_empty</span
									>
									<div class="min-w-0">
										<p
											class="text-black text-xs font-bold leading-tight truncate group-hover:text-win-magenta"
										>
											{job.run_name || "Untitled"}
										</p>
										<p
											class="text-gray-600 text-[9px] font-mono italic"
										>
											#{job.id} • {job.config.steps}s / {job
												.config.scale}c
										</p>
									</div>
								</div>
								<button
									onclick={() => cancelJob(job.id)}
									class="text-black hover:text-red-600 flex-shrink-0"
								>
									<span
										class="material-symbols-outlined text-[14px]"
										>close</span
									>
								</button>
							</div>
						</div>
					{/each}
					{#if queuedJobs.length > 5}
						<p
							class="text-[10px] text-center italic opacity-40 border-t border-dashed border-gray-400 pt-2 font-bold"
						>
							+ {queuedJobs.length - 5} additional jobs pending
						</p>
					{/if}
				</div>
			</div>
		</div>

		<!-- Performance Log Footer -->
		<div class="p-2 bg-[#d4d0c8] border-t-2 border-white">
			<div
				class="flex items-center justify-between bg-black px-2 py-1 mb-1"
			>
				<span
					class="text-[9px] text-white font-bold uppercase tracking-widest"
					>System_Logs.log</span
				>
				<span
					class="material-symbols-outlined text-green-400 text-[14px]"
					>terminal</span
				>
			</div>
			<div
				class="h-48 bg-black win95-inset border-black p-2 font-mono text-[9px] text-green-500 overflow-y-auto custom-scrollbar leading-tight"
			>
				<p class="opacity-50 text-[8px] mb-2">
					// INIT SEQUENCE v1.2.0-PATCH
				</p>
				{#each logs as log}
					<p class="mb-1">{log}</p>
				{/each}
				{#if processingJob || processingAll}
					<p class="text-yellow-400 mt-1 animate-pulse">
						[RUNNING] Worker processing job stack...
					</p>
				{/if}
				{#if !systemOnline}
					<p
						class="text-red-500 mt-1 font-bold animate-pulse bg-red-900/20 p-1"
					>
						[FATAL] CONNECTION LOST - RETRYING...
					</p>
				{/if}
				<p class="mt-2 text-gray-500">_</p>
			</div>
		</div>
	</div>
</div>
