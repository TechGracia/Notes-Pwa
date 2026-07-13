<script>
	import { onMount } from 'svelte';

	// ---------------------------------------------------------------------
	// State
	// ---------------------------------------------------------------------

	/** @type {{id: string, title: string, content: string, createdAt: number, updatedAt: number, favorite: boolean, archived: boolean}[]} */
	let notes = $state([]);

	let hydrated = $state(false); // avoids flashing "no notes" before localStorage loads

	let activeSection = $state('all'); // 'all' | 'favorites' | 'archived'
	let searchQuery = $state('');
	let sidebarOpen = $state(false); // mobile drawer
	let theme = $state('light'); // 'light' | 'dark'

	// Editor (create/edit) modal
	let editorOpen = $state(false);
	let editingId = $state(null); // null = creating a new note
	let editTitle = $state('');
	let editContent = $state('');
	let editError = $state('');

	// Delete confirmation
	let pendingDeleteId = $state(null);

	// Per-card context menu
	let openMenuId = $state(null);

	let titleInputEl = $state(null);
	let saveShortcutLabel = $state('Ctrl');

	// ---------------------------------------------------------------------
	// Derived data
	// ---------------------------------------------------------------------

	const sectionNotes = $derived.by(() => {
		if (activeSection === 'favorites') return notes.filter((n) => n.favorite && !n.archived);
		if (activeSection === 'archived') return notes.filter((n) => n.archived);
		return notes.filter((n) => !n.archived);
	});

	const filteredNotes = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();
		const base = [...sectionNotes].sort((a, b) => b.updatedAt - a.updatedAt);
		if (!query) return base;
		return base.filter(
			(n) => n.title.toLowerCase().includes(query) || n.content.toLowerCase().includes(query)
		);
	});

	const allCount = $derived(notes.filter((n) => !n.archived).length);
	const favoriteCount = $derived(notes.filter((n) => n.favorite && !n.archived).length);
	const archivedCount = $derived(notes.filter((n) => n.archived).length);

	const pageTitle = $derived.by(() => {
		if (activeSection === 'favorites') return 'Favorites';
		if (activeSection === 'archived') return 'Archived';
		return 'My Notes';
	});

	const pageSubtitle = $derived.by(() => {
		if (activeSection === 'favorites') return 'The notes you\u2019ve starred for quick access.';
		if (activeSection === 'archived') return 'Notes you\u2019ve tucked away. Restore them anytime.';
		return 'Capture your ideas and keep everything organized.';
	});

	// ---------------------------------------------------------------------
	// Persistence + migration
	// ---------------------------------------------------------------------

	function createNote(title, content) {
		const now = Date.now();
		return {
			id: crypto.randomUUID(),
			title: title.trim(),
			content: content.trim(),
			createdAt: now,
			updatedAt: now,
			favorite: false,
			archived: false
		};
	}

	/**
	 * Reads notes from localStorage and safely migrates legacy formats:
	 * - very old format: array of plain strings
	 * - anything malformed/missing fields gets backfilled with sane defaults
	 */
	function loadNotes() {
		const raw = localStorage.getItem('notes');
		if (!raw) return [];

		let parsed;
		try {
			parsed = JSON.parse(raw);
		} catch {
			return [];
		}

		if (!Array.isArray(parsed)) return [];

		let migrated = false;

		const result = parsed.map((entry) => {
			if (typeof entry === 'string') {
				migrated = true;
				return createNote(entry.slice(0, 60) || 'Untitled note', entry);
			}
			if (entry && typeof entry === 'object') {
				const needsBackfill =
					typeof entry.id !== 'string' ||
					typeof entry.title !== 'string' ||
					typeof entry.content !== 'string' ||
					typeof entry.createdAt !== 'number' ||
					typeof entry.updatedAt !== 'number' ||
					typeof entry.favorite !== 'boolean' ||
					typeof entry.archived !== 'boolean';

				if (needsBackfill) migrated = true;

				return {
					id: typeof entry.id === 'string' ? entry.id : crypto.randomUUID(),
					title: typeof entry.title === 'string' ? entry.title : 'Untitled note',
					content: typeof entry.content === 'string' ? entry.content : '',
					createdAt: typeof entry.createdAt === 'number' ? entry.createdAt : Date.now(),
					updatedAt: typeof entry.updatedAt === 'number' ? entry.updatedAt : Date.now(),
					favorite: typeof entry.favorite === 'boolean' ? entry.favorite : false,
					archived: typeof entry.archived === 'boolean' ? entry.archived : false
				};
			}
			migrated = true;
			return null;
		});

		const clean = result.filter(Boolean);

		if (migrated) {
			// Persist the migrated structure right away so we don't re-migrate every load.
			localStorage.setItem('notes', JSON.stringify(clean));
		}

		return clean;
	}

	function saveNotes() {
		localStorage.setItem('notes', JSON.stringify(notes));
	}

	// ---------------------------------------------------------------------
	// Theme
	// ---------------------------------------------------------------------

	function applyTheme(next) {
		theme = next;
		document.documentElement.setAttribute('data-theme', next);
		localStorage.setItem('theme', next);
	}

	function toggleTheme() {
		applyTheme(theme === 'light' ? 'dark' : 'light');
	}

	// ---------------------------------------------------------------------
	// Lifecycle
	// ---------------------------------------------------------------------

	onMount(() => {
		notes = loadNotes();
		hydrated = true;

		if (navigator.platform?.toLowerCase().includes('mac')) {
			saveShortcutLabel = '\u2318';
		}

		const savedTheme = localStorage.getItem('theme');
		if (savedTheme === 'light' || savedTheme === 'dark') {
			applyTheme(savedTheme);
		} else {
			const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
			applyTheme(prefersDark ? 'dark' : 'light');
		}

		function handleKeydown(e) {
			if (e.key === 'Escape') {
				if (editorOpen) closeEditor();
				else if (pendingDeleteId) pendingDeleteId = null;
				else if (openMenuId) openMenuId = null;
			}
		}
		window.addEventListener('keydown', handleKeydown);

		function handleClickAway() {
			openMenuId = null;
		}
		window.addEventListener('click', handleClickAway);

		return () => {
			window.removeEventListener('keydown', handleKeydown);
			window.removeEventListener('click', handleClickAway);
		};
	});

	// ---------------------------------------------------------------------
	// Editor actions
	// ---------------------------------------------------------------------

	function openNewNote() {
		editingId = null;
		editTitle = '';
		editContent = '';
		editError = '';
		editorOpen = true;
		sidebarOpen = false;
		queueMicrotask(() => titleInputEl?.focus());
	}

	function openEditNote(note) {
		editingId = note.id;
		editTitle = note.title;
		editContent = note.content;
		editError = '';
		editorOpen = true;
		openMenuId = null;
		queueMicrotask(() => titleInputEl?.focus());
	}

	function closeEditor() {
		editorOpen = false;
		editError = '';
	}

	function saveNote() {
		if (editTitle.trim() === '' && editContent.trim() === '') {
			editError = 'Write something before saving.';
			return;
		}

		if (editingId) {
			notes = notes.map((n) =>
				n.id === editingId
					? { ...n, title: editTitle.trim() || 'Untitled note', content: editContent.trim(), updatedAt: Date.now() }
					: n
			);
		} else {
			notes = [...notes, createNote(editTitle || 'Untitled note', editContent)];
		}

		saveNotes();
		closeEditor();
	}

	function handleEditorKeydown(e) {
		if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
			e.preventDefault();
			saveNote();
		}
	}

	// ---------------------------------------------------------------------
	// Note actions
	// ---------------------------------------------------------------------

	function toggleFavorite(id) {
		notes = notes.map((n) => (n.id === id ? { ...n, favorite: !n.favorite, updatedAt: n.updatedAt } : n));
		saveNotes();
	}

	function toggleArchive(id) {
		notes = notes.map((n) => (n.id === id ? { ...n, archived: !n.archived } : n));
		saveNotes();
		openMenuId = null;
	}

	function requestDelete(id) {
		pendingDeleteId = id;
		openMenuId = null;
	}

	function cancelDelete() {
		pendingDeleteId = null;
	}

	function confirmDelete() {
		notes = notes.filter((n) => n.id !== pendingDeleteId);
		saveNotes();
		pendingDeleteId = null;
	}

	function toggleMenu(id, e) {
		e.stopPropagation();
		openMenuId = openMenuId === id ? null : id;
	}

	// ---------------------------------------------------------------------
	// Formatting helpers
	// ---------------------------------------------------------------------

	function formatDate(timestamp) {
		const date = new Date(timestamp);
		const now = new Date();
		const sameDay =
			date.getDate() === now.getDate() &&
			date.getMonth() === now.getMonth() &&
			date.getFullYear() === now.getFullYear();

		if (sameDay) {
			return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
		}
		return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
	}

	function preview(content) {
		return content.length > 140 ? content.slice(0, 140).trim() + '\u2026' : content;
	}
</script>

<svelte:head>
	<title>Notes PWA</title>
	<meta
		name="description"
		content="Create, save, and manage notes anytime, even without an internet connection."
	/>
</svelte:head>

<div class="app">
	<!-- Mobile top bar with menu toggle -->
	<div class="mobile-topbar">
		<button
			class="icon-btn"
			aria-label="Open navigation"
			onclick={() => (sidebarOpen = true)}
		>
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
		</button>
		<div class="mobile-brand">
			<span class="brand-mark" aria-hidden="true">
				<svg width="20" height="20" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
					<rect x="7" y="3" width="16" height="20" rx="4" fill="var(--accent)" opacity="0.22"/>
					<rect x="3" y="7" width="16" height="20" rx="4" fill="var(--accent)"/>
					<path d="M7.5 15h8M7.5 19h5" stroke="white" stroke-width="1.6" stroke-linecap="round"/>
				</svg>
			</span>
			<span>Notes</span>
		</div>
		<button class="icon-btn" aria-label="Toggle theme" onclick={toggleTheme}>
			{#if theme === 'light'}
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
			{:else}
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
			{/if}
		</button>
	</div>

	{#if sidebarOpen}
		<button class="scrim" aria-label="Close navigation" onclick={() => (sidebarOpen = false)}></button>
	{/if}

	<!-- Sidebar -->
	<aside class="sidebar" class:open={sidebarOpen}>
		<div class="sidebar-brand">
			<span class="brand-mark" aria-hidden="true">
				<svg width="22" height="22" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
					<rect x="7" y="3" width="16" height="20" rx="4" fill="var(--accent)" opacity="0.22"/>
					<rect x="3" y="7" width="16" height="20" rx="4" fill="var(--accent)"/>
					<path d="M7.5 15h8M7.5 19h5" stroke="white" stroke-width="1.6" stroke-linecap="round"/>
				</svg>
			</span>
			<span class="brand-name">Notes</span>
		</div>

		<nav class="nav" aria-label="Note sections">
			<button
				class="nav-item"
				class:active={activeSection === 'all'}
				onclick={() => { activeSection = 'all'; sidebarOpen = false; }}
			>
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h8l6 6v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M14 3v6h6"/></svg>
				<span>All Notes</span>
				{#if allCount > 0}<span class="count">{allCount}</span>{/if}
			</button>

			<button
				class="nav-item"
				class:active={activeSection === 'favorites'}
				onclick={() => { activeSection = 'favorites'; sidebarOpen = false; }}
			>
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
				<span>Favorites</span>
				{#if favoriteCount > 0}<span class="count">{favoriteCount}</span>{/if}
			</button>

			<button
				class="nav-item"
				class:active={activeSection === 'archived'}
				onclick={() => { activeSection = 'archived'; sidebarOpen = false; }}
			>
				<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
				<span>Archived</span>
				{#if archivedCount > 0}<span class="count">{archivedCount}</span>{/if}
			</button>
		</nav>

		<div class="sidebar-footer">
			<button class="nav-item" onclick={toggleTheme}>
				{#if theme === 'light'}
					<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
					<span>Dark mode</span>
				{:else}
					<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
					<span>Light mode</span>
				{/if}
			</button>
		</div>
	</aside>

	<!-- Main content -->
	<div class="content">
	  <div class="page-container">
		<header class="header">
			<div class="header-titles">
				<h1>{pageTitle}</h1>
				<p class="subtitle">{pageSubtitle}</p>
			</div>

			<div class="header-actions">
				<div class="search-field">
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
					<input
						type="text"
						placeholder="Search notes..."
						bind:value={searchQuery}
						aria-label="Search notes"
					/>
				</div>

				<button class="btn-primary" onclick={openNewNote}>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
					<span>New Note</span>
				</button>
			</div>
		</header>

		<main>
			{#if hydrated}
				{#if filteredNotes.length === 0}
					<div class="empty-state">
						{#if searchQuery.trim() !== ''}
							<div class="empty-icon" aria-hidden="true">
								<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
							</div>
							<h2>No matching notes</h2>
							<p>Try a different search term.</p>
						{:else if activeSection === 'favorites'}
							<div class="empty-icon" aria-hidden="true">
								<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
							</div>
							<h2>No favorite notes yet</h2>
							<p>Star a note to see it here.</p>
						{:else if activeSection === 'archived'}
							<div class="empty-icon" aria-hidden="true">
								<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
							</div>
							<h2>No archived notes</h2>
							<p>Notes you archive will show up here.</p>
						{:else}
							<div class="empty-icon" aria-hidden="true">
								<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h8l6 6v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M14 3v6h6"/></svg>
							</div>
							<h2>No notes yet</h2>
							<p>Capture your first idea and keep it somewhere you'll find it.</p>
							<button class="btn-primary" onclick={openNewNote}>
								<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
								<span>Create your first note</span>
							</button>
						{/if}
					</div>
				{:else}
					<div class="note-grid">
						{#each filteredNotes as noteItem (noteItem.id)}
							<article class="note-card">
								<div class="note-card-top">
									<h2 class="note-title">{noteItem.title || 'Untitled note'}</h2>
									<div class="note-card-menu">
										<button
											class="icon-btn small"
											aria-label="More actions for {noteItem.title || 'Untitled note'}"
											aria-expanded={openMenuId === noteItem.id}
											onclick={(e) => toggleMenu(noteItem.id, e)}
										>
											<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="12" cy="19" r="1.6"/></svg>
										</button>
										{#if openMenuId === noteItem.id}
											<div
											class="menu"
											role="menu"
											tabindex="-1"
											onclick={(e) => e.stopPropagation()}
											onkeydown={(e) => e.stopPropagation()}
										>
												<button onclick={() => openEditNote(noteItem)}>Edit</button>
												<button onclick={() => toggleArchive(noteItem.id)}>
													{noteItem.archived ? 'Restore' : 'Archive'}
												</button>
												<button class="danger" onclick={() => requestDelete(noteItem.id)}>Delete</button>
											</div>
										{/if}
									</div>
								</div>

								<p class="note-preview">{preview(noteItem.content) || 'No additional text'}</p>

								<div class="note-card-bottom">
									<span class="note-date">{formatDate(noteItem.updatedAt)}</span>
									<button
										class="icon-btn small favorite"
										class:active={noteItem.favorite}
										aria-label={noteItem.favorite ? 'Remove from favorites' : 'Add to favorites'}
										onclick={() => toggleFavorite(noteItem.id)}
									>
										<svg width="16" height="16" viewBox="0 0 24 24" fill={noteItem.favorite ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
									</button>
								</div>
							</article>
						{/each}
					</div>
				{/if}
			{/if}
		</main>
	  </div>
	</div>
</div>

<!-- Note editor modal -->
{#if editorOpen}
	<div class="modal-scrim" role="presentation" onclick={closeEditor}>
		<div
			class="modal"
			role="dialog"
			aria-modal="true"
			aria-labelledby="editor-heading"
			tabindex="-1"
			onclick={(e) => e.stopPropagation()}
			onkeydown={handleEditorKeydown}
		>
			<h2 id="editor-heading">{editingId ? 'Edit note' : 'New note'}</h2>

			<label class="field-label" for="note-title">Title</label>
			<input
				id="note-title"
				class="title-input"
				type="text"
				placeholder="Note title"
				bind:value={editTitle}
				bind:this={titleInputEl}
			/>

			<label class="field-label" for="note-content">Content</label>
			<textarea
				id="note-content"
				class="content-input"
				placeholder="Write your note..."
				rows="8"
				bind:value={editContent}
			></textarea>

			{#if editError}
				<p class="field-error" role="alert">{editError}</p>
			{/if}

			<div class="modal-actions">
				<button class="btn-secondary" onclick={closeEditor}>Cancel</button>
				<button class="btn-primary" onclick={saveNote}>
					{editingId ? 'Save Changes' : 'Save Note'}
				</button>
			</div>
			<p class="hint">Tip: press {saveShortcutLabel} + Enter to save</p>
		</div>
	</div>
{/if}

<!-- Delete confirmation -->
{#if pendingDeleteId}
	<div class="modal-scrim" role="presentation" onclick={cancelDelete}>
		<div
			class="modal confirm"
			role="alertdialog"
			aria-modal="true"
			aria-labelledby="confirm-heading"
			tabindex="-1"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
		>
			<h2 id="confirm-heading">Delete this note?</h2>
			<p>This action cannot be undone.</p>
			<div class="modal-actions">
				<button class="btn-secondary" onclick={cancelDelete}>Cancel</button>
				<button class="btn-danger" onclick={confirmDelete}>Delete Note</button>
			</div>
		</div>
	</div>
{/if}

<style>
	:global(:root) {
		--space-1: 8px;
		--space-2: 16px;
		--space-3: 24px;
		--space-4: 32px;
		--space-6: 48px;

		--radius-sm: 8px;
		--radius-md: 12px;
		--radius-lg: 16px;

		--ease: cubic-bezier(0.16, 1, 0.3, 1);

		--accent: #6366f1;
		--accent-hover: #4f46e5;
		--accent-soft: #eef0fe;
		--danger: #ef4444;
		--danger-soft: #fdecec;

		--font: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, Roboto, Helvetica, Arial, sans-serif;
	}

	:global([data-theme='light']) {
		--bg: #f7f7fb;
		--surface: #ffffff;
		--surface-hover: #fafaff;
		--border: #e7e7ef;
		--text: #17171f;
		--text-secondary: #6b6b7b;
		--text-tertiary: #9a9aab;
		--shadow: 0 1px 2px rgba(20, 20, 40, 0.04), 0 4px 16px rgba(20, 20, 40, 0.05);
		--scrim: rgba(20, 20, 30, 0.35);
	}

	:global([data-theme='dark']) {
		--bg: #131318;
		--surface: #1b1b22;
		--surface-hover: #212129;
		--border: #2b2b35;
		--text: #f1f1f5;
		--text-secondary: #a4a4b2;
		--text-tertiary: #75757f;
		--shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 8px 24px rgba(0, 0, 0, 0.35);
		--scrim: rgba(0, 0, 0, 0.55);
	}

	:global(html, body) {
		background: var(--bg);
		color: var(--text);
		font-family: var(--font);
	}

	:global(*) {
		box-sizing: border-box;
	}

	.app {
		display: flex;
		min-height: 100vh;
		background: var(--bg);
	}

	/* ---------- Sidebar ---------- */

	.sidebar {
		width: 240px;
		flex-shrink: 0;
		background: var(--surface);
		border-right: 1px solid var(--border);
		padding: var(--space-3) var(--space-2);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.sidebar-brand {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 var(--space-1) var(--space-2);
		margin-bottom: var(--space-1);
		border-bottom: 1px solid var(--border);
	}

	.brand-mark {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 30px;
		height: 30px;
		flex-shrink: 0;
	}

	.brand-name {
		font-weight: 650;
		font-size: 15.5px;
		letter-spacing: -0.015em;
	}

	.nav {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.nav-item {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 10px var(--space-1);
		border-radius: var(--radius-sm);
		border: none;
		background: transparent;
		color: var(--text-secondary);
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		text-align: left;
		transition: background 0.18s var(--ease), color 0.18s var(--ease);
	}

	.nav-item:hover {
		background: var(--surface-hover);
		color: var(--text);
	}

	.nav-item.active {
		background: var(--accent-soft);
		color: var(--accent);
	}

	:global([data-theme='dark']) .nav-item.active {
		background: rgba(99, 102, 241, 0.16);
		color: #a5a8fb;
	}

	.nav-item .count {
		margin-left: auto;
		font-size: 12px;
		color: var(--text-tertiary);
		font-weight: 600;
	}

	.nav-item.active .count {
		color: inherit;
	}

	.sidebar-footer {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		gap: 2px;
		border-top: 1px solid var(--border);
		padding-top: var(--space-2);
	}

	.scrim {
		display: none;
	}

	/* ---------- Mobile top bar ---------- */

	.mobile-topbar {
		display: none;
	}

	/* ---------- Content ---------- */

	.content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.page-container {
		width: 100%;
		max-width: 1120px;
		margin: 0 auto;
		padding: 0 var(--space-4);
		display: flex;
		flex-direction: column;
		flex: 1;
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		padding: var(--space-4) 0 var(--space-3);
		flex-wrap: wrap;
	}

	.header-titles h1 {
		margin: 0;
		font-size: 26px;
		font-weight: 700;
		letter-spacing: -0.02em;
	}

	.subtitle {
		margin: 4px 0 0;
		color: var(--text-secondary);
		font-size: 14px;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.search-field {
		display: flex;
		align-items: center;
		gap: 8px;
		background: var(--bg);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 9px 12px;
		color: var(--text-tertiary);
		width: 260px;
		transition: border-color 0.18s var(--ease), box-shadow 0.18s var(--ease), background 0.18s var(--ease);
	}

	.search-field:focus-within {
		border-color: var(--accent);
		box-shadow: 0 0 0 3px var(--accent-soft);
	}

	.search-field input {
		border: none;
		outline: none;
		background: transparent;
		color: var(--text);
		font-size: 14px;
		width: 100%;
		font-family: inherit;
	}

	.search-field input::placeholder {
		color: var(--text-tertiary);
	}

	/* ---------- Buttons ---------- */

	.btn-primary,
	.btn-secondary,
	.btn-danger {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		border-radius: var(--radius-sm);
		font-size: 14px;
		font-weight: 600;
		padding: 9px 16px;
		border: 1px solid transparent;
		cursor: pointer;
		transition: transform 0.12s var(--ease), background 0.15s var(--ease), border-color 0.15s var(--ease);
		font-family: inherit;
	}

	.btn-primary {
	background: #4f46e5;
	color: #ffffff;
}

	.btn-primary:hover {
	background: #4338ca;
}

	.btn-primary:active {
		transform: scale(0.97);
	}

	.btn-secondary {
		background: var(--surface);
		color: var(--text);
		border-color: var(--border);
	}

	.btn-secondary:hover {
		background: var(--surface-hover);
	}

	.btn-danger {
		background: var(--danger);
		color: white;
	}

	.btn-danger:hover {
		background: #dc2626;
	}

	.icon-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		border-radius: var(--radius-sm);
		border: 1px solid transparent;
		background: transparent;
		color: var(--text-secondary);
		cursor: pointer;
		transition: background 0.15s var(--ease), color 0.15s var(--ease);
	}

	.icon-btn:hover {
		background: var(--surface-hover);
		color: var(--text);
	}

	.icon-btn.small {
		width: 28px;
		height: 28px;
	}

	.icon-btn.favorite:hover {
		background: var(--accent-soft);
		color: var(--accent);
	}

	:global([data-theme='dark']) .icon-btn.favorite:hover {
		background: rgba(99, 102, 241, 0.16);
	}

	.icon-btn.favorite.active {
		color: var(--accent);
	}

	/* ---------- Main / grid ---------- */

	main {
		padding: 0 0 var(--space-6);
		flex: 1;
	}

	.note-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(272px, 336px));
		justify-content: start;
		gap: var(--space-2);
	}

	.note-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-2);
		box-shadow: var(--shadow);
		display: flex;
		flex-direction: column;
		gap: 10px;
		transition: transform 0.2s var(--ease), border-color 0.2s var(--ease), box-shadow 0.2s var(--ease);
		position: relative;
	}

	.note-card:hover {
		transform: translateY(-3px);
		border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
		box-shadow: 0 2px 4px rgba(20, 20, 40, 0.05), 0 10px 24px rgba(20, 20, 40, 0.07);
	}

	:global([data-theme='dark']) .note-card:hover {
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.35), 0 10px 28px rgba(0, 0, 0, 0.4);
	}

	.note-card-top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-1);
	}

	.note-title {
		margin: 0;
		font-size: 16px;
		font-weight: 650;
		letter-spacing: -0.015em;
		line-height: 1.35;
		color: var(--text);
		overflow-wrap: anywhere;
	}

	.note-card-menu {
		position: relative;
		flex-shrink: 0;
	}

	.menu {
		position: absolute;
		right: 0;
		top: 34px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		box-shadow: var(--shadow);
		display: flex;
		flex-direction: column;
		min-width: 140px;
		padding: 4px;
		z-index: 20;
		transform-origin: top right;
		animation: menu-in 0.16s var(--ease);
	}

	.menu button {
		text-align: left;
		background: none;
		border: none;
		font-size: 13px;
		padding: 8px 10px;
		border-radius: 6px;
		color: var(--text);
		cursor: pointer;
		font-family: inherit;
		transition: background 0.15s var(--ease);
	}

	.menu button:hover {
		background: var(--surface-hover);
	}

	.menu button.danger {
		color: var(--danger);
	}

	.note-preview {
		margin: 0;
		font-size: 14px;
		color: var(--text-secondary);
		line-height: 1.55;
		flex: 1;
		overflow-wrap: anywhere;
		display: -webkit-box;
		-webkit-line-clamp: 4;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.note-card-bottom {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: var(--space-1);
	}

	.note-date {
	font-size: 12px;
	font-weight: 500;
	letter-spacing: 0.02em;
	color: var(--text-secondary);
}

	/* ---------- Empty states ---------- */

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		padding: var(--space-6) var(--space-2);
		color: var(--text-secondary);
		gap: 6px;
	}

	.empty-icon {
		color: var(--text-tertiary);
		margin-bottom: var(--space-1);
	}

	.empty-state h2 {
		margin: 0;
		font-size: 17px;
		color: var(--text);
	}

	.empty-state p {
		margin: 0 0 var(--space-2);
		font-size: 14px;
		max-width: 320px;
	}

	/* ---------- Modals ---------- */

	.modal-scrim {
		position: fixed;
		inset: 0;
		background: var(--scrim);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-2);
		z-index: 100;
		animation: fade-in 0.15s var(--ease);
	}

	.modal {
		background: var(--surface);
		border-radius: var(--radius-lg);
		border: 1px solid var(--border);
		box-shadow: var(--shadow);
		padding: var(--space-3);
		width: 100%;
		max-width: 520px;
		max-height: 90vh;
		overflow-y: auto;
		animation: pop-in 0.18s var(--ease);
	}

	.modal.confirm {
		max-width: 380px;
	}

	.modal h2 {
		margin: 0 0 var(--space-2);
		font-size: 18px;
	}

	.field-label {
		display: block;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-secondary);
		margin: var(--space-2) 0 6px;
	}

	.title-input,
	.content-input {
		width: 100%;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 10px 12px;
		font-size: 14px;
		background: var(--bg);
		color: var(--text);
		font-family: inherit;
		outline: none;
		transition: border-color 0.15s var(--ease), box-shadow 0.15s var(--ease);
	}

	.title-input:focus,
	.content-input:focus {
		border-color: var(--accent);
		box-shadow: 0 0 0 3px var(--accent-soft);
	}

	.content-input {
		resize: vertical;
		line-height: 1.5;
		min-height: 140px;
	}

	.field-error {
		color: var(--danger);
		font-size: 13px;
		margin: var(--space-1) 0 0;
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-1);
		margin-top: var(--space-3);
	}

	.hint {
		margin: var(--space-1) 0 0;
		font-size: 12px;
		color: var(--text-tertiary);
		text-align: right;
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes pop-in {
		from { opacity: 0; transform: translateY(6px) scale(0.98); }
		to { opacity: 1; transform: translateY(0) scale(1); }
	}

	@keyframes menu-in {
		from { opacity: 0; transform: scale(0.94) translateY(-4px); }
		to { opacity: 1; transform: scale(1) translateY(0); }
	}

	/* ---------- Focus states ---------- */

	button:focus-visible,
	input:focus-visible,
	textarea:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	/* ---------- Reduced motion ---------- */

	@media (prefers-reduced-motion: reduce) {
		.note-card,
		.modal-scrim,
		.modal,
		.menu,
		.btn-primary,
		.nav-item,
		.icon-btn {
			animation: none !important;
			transition: none !important;
		}
		.note-card:hover {
			transform: none;
		}
	}

	/* ---------- Responsive ---------- */

	@media (max-width: 900px) {
		.sidebar {
			position: fixed;
			top: 0;
			left: 0;
			bottom: 0;
			z-index: 50;
			transform: translateX(-100%);
			transition: transform 0.22s var(--ease);
			width: 260px;
		}

		.sidebar.open {
			transform: translateX(0);
		}

		.scrim {
			display: block;
			position: fixed;
			inset: 0;
			background: var(--scrim);
			border: none;
			z-index: 40;
			padding: 0;
			animation: fade-in 0.15s var(--ease);
		}

		.mobile-topbar {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: var(--space-2);
			border-bottom: 1px solid var(--border);
			background: var(--surface);
			position: sticky;
			top: 0;
			z-index: 30;
		}

		.mobile-brand {
			display: flex;
			align-items: center;
			gap: 8px;
			font-weight: 600;
			font-size: 14px;
		}

		.app {
			flex-direction: column;
		}

		.page-container {
			padding: 0 var(--space-2);
		}

		.header {
			flex-direction: column;
			align-items: stretch;
			padding: var(--space-2) 0;
		}

		.header-actions {
			flex-direction: column;
			align-items: stretch;
		}

		.search-field {
			width: 100%;
		}

		.btn-primary {
			justify-content: center;
			padding: 11px 16px;
		}

		main {
			padding: 0 0 var(--space-4);
		}

		.note-grid {
			grid-template-columns: 1fr;
		}
	}
</style>