<script lang="ts">
	import "../app.css";
	import ToastContainer from "$lib/components/ToastContainer.svelte";
	import { page } from "$app/stores";
	import favicon from "$lib/assets/favicon.svg";
	import { onMount, onDestroy } from "svelte";

	let { children } = $props();
	let unratedCount = $state(0);
	let pollInterval: any;

	interface MenuItem {
		label: string;
		icon: string;
		href: string;
		badge?: number;
	}

	const menuItems: MenuItem[] = $derived([
		{ label: "Home", icon: "home", href: "/" },
		{
			label: "Gallery",
			icon: "photo_library",
			href: "/gallery",
			badge: unratedCount,
		},
		{ label: "Generate", icon: "auto_awesome", href: "/create" },
		{ label: "Analysis", icon: "table_chart", href: "/analysis" },
	]);

	async function fetchUnratedCount() {
		try {
			const res = await fetch(
				"http://localhost:8000/api/images?unrated_only=true&limit=1",
			);
			const data = await res.json();
			unratedCount = data.total;
		} catch (e) {
			console.error("Failed to fetch unrated count", e);
		}
	}

	onMount(() => {
		fetchUnratedCount();
		pollInterval = setInterval(fetchUnratedCount, 10000); // Poll every 10s
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>SinkIn Image Experimentation</title>
</svelte:head>

<div
	class="h-screen flex p-2 gap-3 selection:bg-win-magenta selection:text-white overflow-hidden"
>
	<!-- Sidebar -->
	<aside
		class="w-64 h-full flex flex-col flex-shrink-0 win95-window z-10 font-mono"
	>
		<div class="flex flex-col h-full justify-between">
			<div class="flex flex-col gap-1 p-1">
				<div class="win95-title-bar mb-2">
					<span class="tracking-wider text-[10px]">SYSTEM.CFG</span>
					<button
						class="w-4 h-4 bg-[#c0c0c0] text-black text-[10px] flex items-center justify-center border border-white border-b-black border-r-black leading-none font-bold shadow-sm"
						>x</button
					>
				</div>
				<div
					class="flex gap-3 items-center px-2 py-4 border-2 border-transparent border-b-[#808080] mb-2 bg-gradient-to-r from-white/10 to-transparent"
				>
					<div
						class="bg-center bg-no-repeat bg-cover size-12 flex-shrink-0 border-2 border-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] bg-[url('https://lh3.googleusercontent.com/aida-public/AB6AXuDHdzBVmeRhIKKN5ZynPbYA4xco4Ix-BUAxEhpL_FCy0NODRv5JQASpNlE6uID6K1-fSYUlfi7fq31YnJf7hZPkm-zpydGYk6-BWpdrZTPgef0uC4EyElM0tkTzAMSDhcIYTz-Z5Vu_ip7GPyhiYJI-EENBdnwPLGs3bvmVA_QnQuO_jAhyLj6p_9twcec7YxwdYRK6Cztjc38gyel8IFVtme8zTr_FcaiVTVUiWWW6Y1mWniDUGelVXKjTw9m1bDIPXD6ZTdc8iY8')]"
					></div>
					<div class="flex flex-col overflow-hidden">
						<h1
							class="text-black text-xl font-bold leading-none font-pixel tracking-widest text-win-purple"
						>
							JAM
						</h1>
						<p
							class="text-gray-600 text-[10px] font-bold leading-normal uppercase mt-1 tracking-wider"
						>
							[ MASTER USER ]
						</p>
					</div>
				</div>
				<div class="flex flex-col gap-2 px-2 mt-2">
					{#each menuItems as item}
						<a
							href={item.href}
							class="flex items-center gap-3 px-3 py-2 transition-none group border-2 {$page
								.url.pathname === item.href
								? 'win95-btn bg-win-magenta text-white border-white border-b-black border-r-black'
								: 'border-transparent hover:border-[#ffffff] hover:border-b-[#404040] hover:border-r-[#404040] hover:bg-white/50 no-underline text-black'}"
						>
							<span
								class="material-symbols-outlined text-[20px] {$page
									.url.pathname === item.href
									? 'text-white'
									: 'text-win-purple group-hover:text-win-purple'}"
								>{item.icon}</span
							>
							<div
								class="flex items-center justify-between flex-1"
							>
								<p
									class="text-xs font-bold uppercase tracking-wider"
								>
									{item.label}
								</p>
								{#if item.label === "Gallery"}
									<span
										class="text-[10px] bg-win-magenta text-white px-1.5 py-0.5 border border-white shadow-[1px_1px_0_0_black] font-pixel"
									>
										({item.badge ?? 0})
									</span>
								{:else if item.badge && item.badge > 0}
									<span
										class="text-[10px] bg-win-magenta text-white px-1.5 py-0.5 border border-white shadow-[1px_1px_0_0_black] font-pixel"
									>
										({item.badge})
									</span>
								{/if}
							</div>
						</a>
					{/each}
				</div>
			</div>
			<div class="p-3 border-t-2 border-[#ffffff]">
				<a
					href="/create"
					class="flex w-full cursor-pointer items-center justify-center gap-2 win95-btn h-10 px-4 text-xs font-bold leading-normal tracking-[0.05em] active:bg-gray-400 bg-white no-underline"
				>
					<span
						class="material-symbols-outlined text-[20px] text-green-600"
						>add</span
					>
					<span class="truncate uppercase text-green-700"
						>New Run</span
					>
				</a>
			</div>
		</div>
	</aside>

	<!-- Main Content Area -->
	<main
		class="flex-1 flex flex-col h-full overflow-hidden win95-window relative z-10"
	>
		{@render children()}
	</main>
</div>
<ToastContainer />
