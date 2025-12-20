<script lang="ts">
	import "../app.css";
	import Navbar from "$lib/components/Navbar.svelte";
	import ToastContainer from "$lib/components/ToastContainer.svelte";
	import favicon from "$lib/assets/favicon.svg";

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>SinkIn Image Experimentation</title>
</svelte:head>

<div data-theme="dark" class="min-h-screen bg-base-100 flex flex-col">
	<Navbar />
	<main class="flex-1 container mx-auto p-4 md:p-8">
		{@render children()}
	</main>
	<ToastContainer />
</div>
