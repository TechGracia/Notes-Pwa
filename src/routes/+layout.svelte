<script>
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<link rel="manifest" href="/manifest.webmanifest" />
	<meta name="theme-color" content="#4f46e5" />
	<meta
		name="viewport"
		content="width=device-width, initial-scale=1"
	/>
</svelte:head>

{@render children()}