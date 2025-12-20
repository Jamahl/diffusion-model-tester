<script lang="ts">
	import { onMount } from "svelte";
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
	let error = $state<string | null>(null);

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

	async function runNextJob() {
		if (queuedJobs.length === 0 || processingJob) return;

		processingJob = true;
		const nextJob = queuedJobs[queuedJobs.length - 1]; // list_jobs is desc, so last is oldest? wait.
		// Actually list_jobs is desc, so oldest is at the end.
		// Better to use /api/jobs/next which sorts by asc

		try {
			const nextRes = await fetch("http://localhost:8000/api/jobs/next");
			const { job_id } = await nextRes.json();

			if (!job_id) {
				alert("No jobs in queue");
				return;
			}

			const res = await fetch("http://localhost:8000/api/jobs/run", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ job_id }),
			});

			if (!res.ok) throw new Error("Failed to run job");

			toasts.success(`Job completed successfully`);
			// Refresh
			await Promise.all([fetchRuns(), fetchQueue()]);
		} catch (e: any) {
			toasts.error("Error running job: " + e.message);
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

	function formatDate(dateStr: string) {
		return new Date(dateStr).toLocaleString();
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

	onMount(async () => {
		loading = true;
		await Promise.all([fetchRuns(), fetchQueue()]);
		loading = false;

		// Poll for updates
		const interval = setInterval(() => {
			fetchRuns();
			fetchQueue();
		}, 5000);
		return () => clearInterval(interval);
	});
</script>

<div class="flex flex-col gap-8">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold font-display italic tracking-tight">
				Experiment Dashboard
			</h1>
			<p class="text-base-content/60">
				Monitor and review your generative AI batches.
			</p>
		</div>
		<div class="flex gap-3">
			<a
				href="http://localhost:8000/api/analysis/csv"
				class="btn btn-outline"
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
			<a href="/create" class="btn btn-primary">
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
						d="M12 4.5v15m7.5-7.5h-15"
					/>
				</svg>
				New Experiment
			</a>
		</div>
	</div>

	{#if queuedJobs.length > 0 || processingJob}
		<div
			class="card bg-secondary/5 border border-secondary/20 shadow-xl overflow-hidden"
		>
			<div class="card-body p-6">
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-3">
						<div
							class="w-10 h-10 rounded-full bg-secondary/20 flex items-center justify-center text-secondary"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-6 h-6"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
								/>
							</svg>
						</div>
						<div>
							<h2 class="text-xl font-bold text-secondary">
								Active Queue
							</h2>
							<p
								class="text-xs opacity-60 uppercase tracking-widest font-semibold"
							>
								{queuedJobs.length} Jobs Remaining
							</p>
						</div>
					</div>
					<div class="flex gap-2">
						<button
							onclick={cancelAll}
							class="btn btn-ghost btn-sm text-error border-error/20 hover:bg-error/10"
							disabled={processingJob}
						>
							Cancel All
						</button>
						<button
							onclick={runNextJob}
							class="btn btn-secondary btn-sm px-6"
							disabled={processingJob}
						>
							{#if processingJob}
								<span class="loading loading-spinner loading-xs"
								></span>
								Processing...
							{:else}
								Run Next
							{/if}
						</button>
					</div>
				</div>

				<div
					class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"
				>
					{#each queuedJobs.slice(0, 6) as job: Job (job.id)}
						<div
							class="bg-base-200/50 rounded-lg p-3 border border-white/5 flex flex-col justify-between"
						>
							<div>
								<div
									class="flex items-center justify-between mb-1"
								>
									<span
										class="text-[10px] font-bold opacity-40 uppercase"
										>Job #{job.id}</span
									>
									<div class="flex gap-1 items-center">
										<span
											class="badge badge-secondary badge-outline badge-xs text-[9px]"
											>{job.run_batch}</span
										>
										<button
											onclick={() => cancelJob(job.id)}
											class="btn btn-ghost btn-xs btn-circle text-error h-4 w-4 min-h-0"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2"
												stroke="currentColor"
												class="w-3 h-3"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M6 18L18 6M6 6l12 12"
												/>
											</svg>
										</button>
									</div>
								</div>
								<div
									class="text-xs font-semibold truncate mb-1"
								>
									RUN: {job.run_name}
								</div>
								<div
									class="text-[10px] opacity-70 line-clamp-2 italic"
								>
									"{job.config.steps} steps • {job.config
										.scale} CFG"
								</div>
							</div>
						</div>
					{/each}
					{#if queuedJobs.length > 6}
						<div
							class="bg-base-200/20 rounded-lg p-3 border border-dashed border-white/10 flex items-center justify-center text-xs opacity-40 italic"
						>
							+ {queuedJobs.length - 6} more jobs...
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	{#if loading}
		<div class="flex justify-center py-20">
			<span class="loading loading-spinner loading-lg text-primary"
			></span>
		</div>
	{:else if error}
		<div class="alert alert-error">
			<span>{error}</span>
		</div>
	{:else if runs.length === 0}
		<div class="card bg-base-200 shadow-xl">
			<div class="card-body items-center text-center py-20">
				<div class="bg-base-300 p-6 rounded-full mb-4">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="w-12 h-12 opacity-20"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
						/>
					</svg>
				</div>
				<h2 class="card-title">No runs found</h2>
				<p class="text-base-content/60">
					Start your first experiment to see it here.
				</p>
				<div class="card-actions mt-6">
					<a href="/create" class="btn btn-primary btn-outline"
						>Create First Run</a
					>
				</div>
			</div>
		</div>
	{:else}
		<div class="overflow-x-auto bg-base-200 rounded-xl shadow-xl">
			<table class="table table-zebra">
				<thead>
					<tr>
						<th>Batch</th>
						<th>Details</th>
						<th>Progress</th>
						<th>Stats</th>
						<th>Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each runs as run: Run}
						<tr class="hover">
							<td class="font-mono text-lg font-bold"
								>#{run.batch_number}</td
							>
							<td>
								<div class="max-w-md">
									<div class="font-bold truncate">
										{run.name}
									</div>
									<div class="text-xs opacity-50">
										{run.model_id} • {formatDate(
											run.created_at,
										)}
									</div>
									<div
										class="text-xs italic truncate mt-1 opacity-70"
									>
										"{run.prompt}"
									</div>
								</div>
							</td>
							<td>
								<div class="flex flex-col gap-1 min-w-[120px]">
									<div class="flex justify-between text-xs">
										<span>Rated</span>
										<span
											>{run.total_images -
												run.unrated_count} / {run.total_images}</span
										>
									</div>
									<progress
										class="progress progress-primary w-full"
										value={run.total_images -
											run.unrated_count}
										max={run.total_images}
									></progress>
								</div>
							</td>
							<td>
								<div class="flex flex-col gap-1">
									<div class="flex gap-2">
										{#if run.queued_jobs > 0}
											<div
												class="badge badge-warning gap-1 badge-sm"
											>
												<span
													class="loading loading-spinner loading-xs"
												></span>
												{run.queued_jobs} Q
											</div>
										{/if}
										{#if run.upscaled_count > 0}
											<div
												class="badge badge-secondary badge-sm"
											>
												{run.upscaled_count} UP
											</div>
										{/if}
										{#if run.unrated_count === 0 && run.total_images > 0}
											<div
												class="badge badge-success badge-sm"
											>
												Rated
											</div>
										{/if}
									</div>
									<div
										class="text-[10px] font-mono opacity-50 flex items-center gap-1 mt-1"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="w-3 h-3 text-secondary"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
											/>
										</svg>
										{run.total_cost.toFixed(2)} credits
									</div>
								</div>
							</td>
							<td>
								<a
									href="/runs/{run.id}"
									class="btn btn-ghost btn-sm">Review</a
								>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
