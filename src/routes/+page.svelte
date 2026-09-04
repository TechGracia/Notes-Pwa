<script>
	import { onMount } from 'svelte';
	import {
		getCurrentUser,
		getNotes,
		createNote,
		updateNote,
		deleteNote,
		changePassword,
		logout
	} from '$lib/api.js';

	// =========================================================
	// CONSTANTS
	// =========================================================

	const TITLE_LIMIT = 100;
	const CONTENT_LIMIT = 5000;

	const NOTE_CATEGORIES = [
		{ label: 'IDEAS', className: 'ideas' },
		{ label: 'STUDY', className: 'study' },
		{ label: 'TRAVEL', className: 'travel' },
		{ label: 'HEALTH', className: 'health' },
		{ label: 'WORK', className: 'work' },
		{ label: 'PERSONAL', className: 'personal' }
	];

	// =========================================================
	// CORE STATE
	// =========================================================

	let notes = $state([]);
	let loading = $state(true);
	let error = $state('');
	let search = $state('');
	let currentUser = $state(null);

	// =========================================================
	// NOTE EDITOR
	// =========================================================

	let showNoteModal = $state(false);
	let editingNote = $state(null);
	let title = $state('');
	let content = $state('');
	let saving = $state(false);

	// =========================================================
	// DELETE MODAL
	// =========================================================

	let showDeleteModal = $state(false);
	let noteToDelete = $state(null);
	let deleting = $state(false);

	// =========================================================
	// PASSWORD MODAL
	// =========================================================

	let showPasswordModal = $state(false);
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let passwordSaving = $state(false);
	let passwordError = $state('');
	let showCurrentPassword = $state(false);
	let showNewPassword = $state(false);
	let showConfirmPassword = $state(false);

	// =========================================================
	// MOBILE
	// =========================================================

	let mobileMenuOpen = $state(false);

	// =========================================================
	// TOAST
	// =========================================================

	let toast = $state({
		show: false,
		type: 'success',
		message: ''
	});

	let toastTimer;
	let searchInput;

	// =========================================================
	// DERIVED STATE
	// =========================================================

	let filteredNotes = $derived.by(() => {
		const query = search.toLowerCase().trim();

		if (!query) return notes;

		return notes.filter((note) => {
			return (
				(note.title ?? '').toLowerCase().includes(query) ||
				(note.content ?? '').toLowerCase().includes(query)
			);
		});
	});

	let noteCountText = $derived(
		`${filteredNotes.length} ${filteredNotes.length === 1 ? 'note' : 'notes'}`
	);

	let isGoogleUser = $derived(
		currentUser?.auth_provider === 'google'
	);

	let canSaveNote = $derived(
		!saving &&
		title.trim().length > 0 &&
		content.trim().length > 0 &&
		title.length <= TITLE_LIMIT &&
		content.length <= CONTENT_LIMIT
	);

	let passwordLongEnough = $derived(newPassword.length >= 6);
	let passwordsMatch = $derived(
		confirmPassword.length > 0 &&
		newPassword === confirmPassword
	);
	let passwordChanged = $derived(
		newPassword.length > 0 &&
		currentPassword.length > 0 &&
		newPassword !== currentPassword
	);

	// =========================================================
	// STARTUP + KEYBOARD SHORTCUTS
	// =========================================================

	onMount(() => {
		initializeDashboard();

		function handleKeyboard(event) {
			const isCtrlOrCmd = event.ctrlKey || event.metaKey;

			if (
				isCtrlOrCmd &&
				event.key.toLowerCase() === 'k'
			) {
				event.preventDefault();
				searchInput?.focus();
				return;
			}

			if (
				isCtrlOrCmd &&
				event.key === 'Enter' &&
				showNoteModal &&
				canSaveNote
			) {
				event.preventDefault();
				saveNote();
				return;
			}

			if (event.key === 'Escape') {
				if (showDeleteModal && !deleting) {
					closeDeleteModal();
					return;
				}

				if (showNoteModal && !saving) {
					closeNoteModal();
					return;
				}

				if (showPasswordModal && !passwordSaving) {
					closePasswordModal();
					return;
				}

				if (mobileMenuOpen) {
					mobileMenuOpen = false;
				}
			}
		}

		window.addEventListener('keydown', handleKeyboard);

		return () => {
			window.removeEventListener('keydown', handleKeyboard);

			if (toastTimer) {
				clearTimeout(toastTimer);
			}
		};
	});

	async function initializeDashboard() {
    const token = sessionStorage.getItem('access_token');

    console.log(
        'Dashboard authentication check. Token exists:',
        !!token
    );

    if (!token) {
        console.log(
            'No authentication token. Redirecting to login.'
        );

        window.location.replace('/login');
        return;
    }

    try {
        currentUser = await getCurrentUser();

        console.log(
            'Dashboard authentication successful:',
            currentUser
        );

        await loadNotes();

    } catch (err) {
        console.error(
            'Authentication check failed:',
            err
        );

        logout();

        window.location.replace('/login');
    }
}

	// =========================================================
	// TOASTS
	// =========================================================

	function showToast(message, type = 'success') {
		if (toastTimer) {
			clearTimeout(toastTimer);
		}

		toast = {
			show: true,
			type,
			message
		};

		toastTimer = setTimeout(() => {
			toast = {
				...toast,
				show: false
			};
		}, 3000);
	}

	function closeToast() {
		if (toastTimer) {
			clearTimeout(toastTimer);
		}

		toast = {
			...toast,
			show: false
		};
	}

	// =========================================================
	// NOTES
	// =========================================================

	async function loadNotes() {
		loading = true;
		error = '';

		try {
			notes = await getNotes();
		} catch (err) {
			console.error(err);

			const message = err?.message?.toLowerCase?.() || '';

			if (
				err?.message?.includes('401') ||
				message.includes('unauthorized')
			) {
				logout();
				window.location.replace('/login');
				return;
			}

			error =
				err?.message ||
				'Could not load your notes from the server.';
		} finally {
			loading = false;
		}
	}

	function openNewNote() {
		editingNote = null;
		title = '';
		content = '';
		error = '';
		showNoteModal = true;
		mobileMenuOpen = false;
	}

	function openEdit(note) {
		editingNote = note;
		title = note.title ?? '';
		content = note.content ?? '';
		error = '';
		showNoteModal = true;
	}

	function closeNoteModal() {
		if (saving) return;

		showNoteModal = false;
		editingNote = null;
		title = '';
		content = '';
	}

	async function saveNote() {
		if (!canSaveNote) return;

		const trimmedTitle = title.trim();
		const trimmedContent = content.trim();
		const wasEditing = Boolean(editingNote);

		saving = true;
		error = '';

		try {
			if (editingNote) {
				await updateNote(
					editingNote.id,
					trimmedTitle,
					trimmedContent
				);
			} else {
				await createNote(
					trimmedTitle,
					trimmedContent
				);
			}

			showNoteModal = false;
			editingNote = null;
			title = '';
			content = '';

			await loadNotes();

			showToast(
				wasEditing
					? 'Note updated successfully.'
					: 'Note created successfully.'
			);
		} catch (err) {
			console.error(err);

			const message =
				err?.message ||
				'Failed to save your note.';

			error = message;
			showToast(message, 'error');
		} finally {
			saving = false;
		}
	}

	// =========================================================
	// DELETE
	// =========================================================

	function requestDelete(note) {
		noteToDelete = note;
		showDeleteModal = true;
	}

	function closeDeleteModal() {
		if (deleting) return;

		showDeleteModal = false;
		noteToDelete = null;
	}

	async function confirmDelete() {
		if (!noteToDelete || deleting) return;

		deleting = true;
		error = '';

		try {
			await deleteNote(noteToDelete.id);

			showDeleteModal = false;
			noteToDelete = null;

			await loadNotes();

			showToast('Note deleted successfully.');
		} catch (err) {
			console.error(err);

			const message =
				err?.message ||
				'Failed to delete the note.';

			error = message;
			showToast(message, 'error');
		} finally {
			deleting = false;
		}
	}

	// =========================================================
	// PASSWORD
	// =========================================================

	function openPasswordModal() {
		if (isGoogleUser) return;

		currentPassword = '';
		newPassword = '';
		confirmPassword = '';
		passwordError = '';
		showCurrentPassword = false;
		showNewPassword = false;
		showConfirmPassword = false;
		showPasswordModal = true;
		mobileMenuOpen = false;
	}

	function closePasswordModal() {
		if (passwordSaving) return;

		showPasswordModal = false;
		currentPassword = '';
		newPassword = '';
		confirmPassword = '';
		passwordError = '';
	}

	async function handleChangePassword() {
		passwordError = '';

		if (!currentPassword || !newPassword || !confirmPassword) {
			passwordError = 'Please fill in all password fields.';
			return;
		}

		if (!passwordLongEnough) {
			passwordError =
				'New password must be at least 6 characters.';
			return;
		}

		if (!passwordChanged) {
			passwordError =
				'New password must be different from the current password.';
			return;
		}

		if (!passwordsMatch) {
			passwordError = 'New passwords do not match.';
			return;
		}

		passwordSaving = true;

		try {
			await changePassword(
				currentPassword,
				newPassword
			);

			showPasswordModal = false;
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';

			showToast('Password changed successfully.');
		} catch (err) {
			console.error(err);

			passwordError =
				err?.message ||
				'Failed to change your password.';
		} finally {
			passwordSaving = false;
		}
	}

	// =========================================================
	// LOGOUT
	// =========================================================

	function handleLogout() {
		logout();
		window.location.href = '/login';
	}

	// =========================================================
	// HELPERS
	// =========================================================

	function getNoteCategory(index) {
		return NOTE_CATEGORIES[index % NOTE_CATEGORIES.length];
	}

	function getInitial(email) {
		if (!email) return 'U';
		return email.charAt(0).toUpperCase();
	}

	// API timestamps are stored by the backend in UTC but may be
	// returned without a timezone suffix, e.g.:
	// "2026-09-03T19:00:00".
	// Without the "Z", JavaScript interprets that value as LOCAL time.
	// That can make a note created on 4 Sep (IST) appear as 3 Sep.
	function parseApiDate(value) {
		if (!value) return null;

		if (value instanceof Date) {
			return Number.isNaN(value.getTime()) ? null : value;
		}

		const raw = String(value).trim();
		if (!raw) return null;

		// If the API did not include a timezone, treat the timestamp as UTC.
		const hasTimezone =
			/[zZ]$/.test(raw) ||
			/[+-]\\d{2}:?\\d{2}$/.test(raw);

		const normalized = hasTimezone ? raw : `${raw}Z`;
		const date = new Date(normalized);

		return Number.isNaN(date.getTime()) ? null : date;
	}

	function formatDate(dateString) {
		const date = parseApiDate(dateString);

		if (!date) return 'Recently';

		const now = new Date();
		const sameDay =
			date.getFullYear() === now.getFullYear() &&
			date.getMonth() === now.getMonth() &&
			date.getDate() === now.getDate();

		if (sameDay) {
			return `Today, ${date.toLocaleTimeString('en-IN', {
				hour: 'numeric',
				minute: '2-digit'
			})}`;
		}

		return date.toLocaleDateString('en-IN', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	function latestNoteDate() {
		if (!notes.length) return 'No activity';

		const timestamps = notes
			.map((note) => note.updated_at ?? note.created_at)
			.map(parseApiDate)
			.filter(Boolean);

		if (!timestamps.length) return 'Recently';

		const latest = timestamps.reduce((a, b) =>
			a > b ? a : b
		);

		return formatDate(latest);
	}
</script>

<svelte:head>
	<title>My Notes</title>
	<meta
		name="description"
		content="Manage your personal notes"
	/>
</svelte:head>

<div class="notes-app">

	<!-- =====================================================
	     MOBILE TOP BAR
	====================================================== -->

	<header class="mobile-topbar">
		<div class="mobile-brand">
			<div class="brand-icon compact">
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
					<polyline points="14 2 14 8 20 8" />
					<line x1="8" y1="13" x2="16" y2="13" />
					<line x1="8" y1="17" x2="14" y2="17" />
				</svg>
			</div>

			<span>Notes</span>
		</div>

		<div class="mobile-actions">
			<button
				type="button"
				class="mobile-create"
				onclick={openNewNote}
				aria-label="Create note"
			>
				+
			</button>

			<button
				type="button"
				class="mobile-menu-button"
				onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
				aria-label="Toggle menu"
				aria-expanded={mobileMenuOpen}
			>
				{#if mobileMenuOpen}
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
					>
						<line x1="6" y1="6" x2="18" y2="18" />
						<line x1="18" y1="6" x2="6" y2="18" />
					</svg>
				{:else}
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
					>
						<line x1="4" y1="7" x2="20" y2="7" />
						<line x1="4" y1="12" x2="20" y2="12" />
						<line x1="4" y1="17" x2="20" y2="17" />
					</svg>
				{/if}
			</button>
		</div>
	</header>

	{#if mobileMenuOpen}
		<button
			type="button"
			class="mobile-overlay"
			onclick={() => (mobileMenuOpen = false)}
			aria-label="Close menu"
		></button>
	{/if}

	<!-- =====================================================
	     SIDEBAR
	====================================================== -->

	<aside class:mobile-open={mobileMenuOpen} class="sidebar">
		<div class="sidebar-top">
			<div class="brand">
				<div class="brand-icon">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
						<polyline points="14 2 14 8 20 8" />
						<line x1="8" y1="13" x2="16" y2="13" />
						<line x1="8" y1="17" x2="14" y2="17" />
					</svg>
				</div>

				<div>
					<div class="brand-name">Notes</div>
					<div class="brand-subtitle">
						Personal workspace
					</div>
				</div>
			</div>

			<div class="sidebar-section">
				<div class="section-label">
					Workspace
				</div>

				<button
					type="button"
					class="nav-item active"
					onclick={() => (mobileMenuOpen = false)}
				>
					<span class="nav-item-icon">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<rect x="4" y="4" width="6" height="6" />
							<rect x="14" y="4" width="6" height="6" />
							<rect x="4" y="14" width="6" height="6" />
							<rect x="14" y="14" width="6" height="6" />
						</svg>
					</span>

					<span>All Notes</span>

					<span class="nav-count">
						{notes.length}
					</span>
				</button>
			</div>

			<button
				type="button"
				class="new-sidebar-button"
				onclick={openNewNote}
			>
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2.2"
					stroke-linecap="round"
				>
					<line x1="12" y1="5" x2="12" y2="19" />
					<line x1="5" y1="12" x2="19" y2="12" />
				</svg>

				<span>Create Note</span>
			</button>
		</div>

		<div class="sidebar-bottom">
			{#if currentUser}
				<div class="user-card">
					<div class="user-avatar">
						{getInitial(currentUser.email)}
					</div>

					<div class="user-details">
						<span class="user-label">
							SIGNED IN AS
						</span>

						<span
							class="user-email"
							title={currentUser.email}
						>
							{currentUser.email}
						</span>

						{#if isGoogleUser}
							<span class="provider-badge">
								Google account
							</span>
						{:else}
							<span class="provider-badge">
								Local account
							</span>
						{/if}
					</div>
				</div>
			{/if}

			{#if isGoogleUser}
				<div class="google-password-info">
					<span class="sidebar-action-icon">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<rect
								x="3"
								y="11"
								width="18"
								height="10"
								rx="2"
							/>
							<path d="M7 11V7a5 5 0 0 1 10 0v4" />
						</svg>
					</span>

					<span>Password managed by Google</span>
				</div>
			{:else}
				<button
					type="button"
					class="sidebar-action"
					onclick={openPasswordModal}
				>
					<span class="sidebar-action-icon">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<rect
								x="3"
								y="11"
								width="18"
								height="10"
								rx="2"
							/>
							<path d="M7 11V7a5 5 0 0 1 10 0v4" />
						</svg>
					</span>

					<span>Change Password</span>
				</button>
			{/if}

			<button
				type="button"
				class="sidebar-action logout"
				onclick={handleLogout}
			>
				<span class="sidebar-action-icon">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
						<polyline points="16 17 21 12 16 7" />
						<line x1="21" y1="12" x2="9" y2="12" />
					</svg>
				</span>

				<span>Logout</span>
			</button>
		</div>
	</aside>

	<!-- =====================================================
	     MAIN
	====================================================== -->

	<main class="main-content">
		<div class="content-container">

			<header class="top-header">
				<div class="header-copy">
					<div class="eyebrow">
						YOUR WORKSPACE
					</div>

					<h1>My Notes</h1>

					<p>
						Capture ideas, thoughts, and important
						information in one secure place.
					</p>
				</div>

				<button
					type="button"
					class="new-note-button"
					onclick={openNewNote}
				>
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2.2"
						stroke-linecap="round"
					>
						<line x1="12" y1="5" x2="12" y2="19" />
						<line x1="5" y1="12" x2="19" y2="12" />
					</svg>

					New Note
				</button>
			</header>

			<!-- STATS -->

			<div class="stats-row">
				<div class="stat-card">
					<div class="stat-icon purple">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<rect
								x="4"
								y="4"
								width="16"
								height="16"
								rx="2"
							/>
							<line x1="8" y1="9" x2="16" y2="9" />
							<line x1="8" y1="13" x2="16" y2="13" />
							<line x1="8" y1="17" x2="13" y2="17" />
						</svg>
					</div>

					<div class="stat-content">
						<span class="stat-label">
							Total Notes
						</span>

						<strong class="stat-value">
							{notes.length}
						</strong>
					</div>
				</div>

				<div class="stat-card">
					<div class="stat-icon blue">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<circle cx="12" cy="12" r="9" />
							<polyline points="12 7 12 12 15 14" />
						</svg>
					</div>

					<div class="stat-content">
						<span class="stat-label">
							Last Updated
						</span>

						<strong class="stat-value">
							{latestNoteDate()}
						</strong>
					</div>
				</div>

				<div class="stat-card">
					<div class="stat-icon green">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
							<polyline points="9 12 11 14 15 10" />
						</svg>
					</div>

					<div class="stat-content">
						<span class="stat-label">
							Account
						</span>

						<strong class="stat-value protected">
							Protected
						</strong>
					</div>
				</div>
			</div>

			<!-- NOTES HEADER / SEARCH -->

			<section class="notes-section">
				<div class="toolbar">
					<div class="toolbar-title">
						<div>
							<h2>
								{search
									? 'Search Results'
									: 'Your Notes'}
							</h2>

							<p>
								{search
									? `Showing ${filteredNotes.length} of ${notes.length} notes`
									: 'Everything you save stays in your personal workspace.'}
							</p>
						</div>

						<span class="result-count">
							{noteCountText}
						</span>
					</div>

					<div class="search-container">
						<svg
							class="search-svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<circle cx="11" cy="11" r="8" />
							<line
								x1="21"
								y1="21"
								x2="16.65"
								y2="16.65"
							/>
						</svg>

						<input
							bind:this={searchInput}
							type="text"
							bind:value={search}
							placeholder="Search notes..."
							aria-label="Search notes"
						/>

						<span class="search-shortcut">
							Ctrl K
						</span>

						{#if search}
							<button
								type="button"
								class="clear-search"
								onclick={() => (search = '')}
								aria-label="Clear search"
							>
								×
							</button>
						{/if}
					</div>
				</div>

				{#if error}
					<div class="error-message">
						<div class="error-icon">
							!
						</div>

						<div class="error-text">
							<strong>
								Something went wrong
							</strong>

							<span>
								{error}
							</span>
						</div>

						<button
							type="button"
							class="error-close"
							onclick={() => (error = '')}
							aria-label="Close error"
						>
							×
						</button>
					</div>
				{/if}

				<!-- SKELETON LOADING -->

				{#if loading}
					<div class="notes-grid">
						{#each Array(3) as _}
							<div
								class="note-card skeleton-card"
								aria-hidden="true"
							>
								<div class="skeleton-top">
									<div class="skeleton skeleton-badge"></div>
									<div class="skeleton-actions">
										<div class="skeleton skeleton-circle"></div>
										<div class="skeleton skeleton-circle"></div>
									</div>
								</div>

								<div class="skeleton skeleton-title"></div>
								<div class="skeleton skeleton-line"></div>
								<div class="skeleton skeleton-line short"></div>

								<div class="skeleton-footer">
									<div class="skeleton skeleton-date"></div>
								</div>
							</div>
						{/each}
					</div>

				{:else if filteredNotes.length > 0}

					<div class="notes-grid">
						{#each filteredNotes as note, index}
							<article class={`note-card ${getNoteCategory(index).className}`}>
								<div class="note-card-top">
									<span class="note-category">
										{getNoteCategory(index).label}
									</span>

									<div class="note-actions">
										<button
											type="button"
											class="icon-button edit"
											onclick={() => openEdit(note)}
											aria-label="Edit note"
											title="Edit note"
										>
											<svg
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											>
												<path d="M12 20h9" />
												<path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
											</svg>
										</button>

										<button
											type="button"
											class="icon-button delete"
											onclick={() => requestDelete(note)}
											aria-label="Delete note"
											title="Delete note"
										>
											<svg
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											>
												<polyline points="3 6 5 6 21 6" />
												<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
												<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
											</svg>
										</button>
									</div>
								</div>

								<div class="note-card-content">
									<h3>
										{note.title}
									</h3>

									<p>
										{note.content}
									</p>
								</div>

								<div class="note-footer">
									<div class="note-date">
										<svg
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<circle cx="12" cy="12" r="9" />
											<polyline points="12 7 12 12 15 14" />
										</svg>

										<span>
											Updated
											{formatDate(
												note.updated_at ??
												note.created_at
											)}
										</span>
									</div>
								</div>
							</article>
						{/each}
					</div>

				{:else if search}

					<div class="empty-state">
						<div class="empty-icon">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<circle cx="11" cy="11" r="8" />
								<line
									x1="21"
									y1="21"
									x2="16.65"
									y2="16.65"
								/>
							</svg>
						</div>

						<h2>No notes found</h2>

						<p>
							Nothing matched
							<strong>"{search}"</strong>.
						</p>

						<button
							type="button"
							class="secondary-button"
							onclick={() => (search = '')}
						>
							Clear Search
						</button>
					</div>

				{:else}

					<div class="empty-state">
						<div class="empty-icon">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.7"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
								<polyline points="14 2 14 8 20 8" />
								<line x1="8" y1="13" x2="16" y2="13" />
								<line x1="8" y1="17" x2="13" y2="17" />
							</svg>
						</div>

						<h2>No notes yet</h2>

						<p>
							Your ideas deserve a place.
							Create your first note to get started.
						</p>

						<button
							type="button"
							class="new-note-button empty-button"
							onclick={openNewNote}
						>
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2.2"
								stroke-linecap="round"
							>
								<line x1="12" y1="5" x2="12" y2="19" />
								<line x1="5" y1="12" x2="19" y2="12" />
							</svg>

							Create Your First Note
						</button>
					</div>
				{/if}
			</section>
		</div>
	</main>

	<!-- =====================================================
	     NOTE MODAL
	====================================================== -->

	{#if showNoteModal}
		<div
			class="modal-backdrop"
			role="presentation"
			onclick={(event) => {
				if (event.target === event.currentTarget) {
					closeNoteModal();
				}
			}}
		>
			<div
				class="modal note-modal"
				role="dialog"
				aria-modal="true"
				aria-labelledby="note-modal-title"
				tabindex="-1"
			>
				<div class="modal-header">
					<div class="modal-header-icon">
						{#if editingNote}
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M12 20h9" />
								<path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
							</svg>
						{:else}
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
								<polyline points="14 2 14 8 20 8" />
								<line x1="8" y1="13" x2="16" y2="13" />
								<line x1="8" y1="17" x2="13" y2="17" />
							</svg>
						{/if}
					</div>

					<div class="modal-title-area">
						<h2 id="note-modal-title">
							{editingNote
								? 'Edit Note'
								: 'Create New Note'}
						</h2>

						<p>
							{editingNote
								? 'Update your note and save your changes.'
								: 'Capture something worth remembering.'}
						</p>
					</div>

					<button
						type="button"
						class="modal-close"
						onclick={closeNoteModal}
						aria-label="Close"
					>
						×
					</button>
				</div>

				<div class="modal-body">
					<div class="form-group">
						<div class="label-row">
							<label for="note-title">
								Title
							</label>

							<span
								class:counter-warning={title.length > TITLE_LIMIT}
							>
								{title.length} / {TITLE_LIMIT}
							</span>
						</div>

						<input
							id="note-title"
							type="text"
							bind:value={title}
							maxlength={TITLE_LIMIT}
							placeholder="Give your note a clear title..."
							autocomplete="off"
							disabled={saving}
						/>
					</div>

					<div class="form-group">
						<div class="label-row">
							<label for="note-content">
								Content
							</label>

							<span
								class:counter-warning={content.length > CONTENT_LIMIT}
							>
								{content.length} / {CONTENT_LIMIT}
							</span>
						</div>

						<textarea
							id="note-content"
							bind:value={content}
							maxlength={CONTENT_LIMIT}
							placeholder="Start writing..."
							rows="10"
							disabled={saving}
						></textarea>
					</div>

					<div class="keyboard-tip">
						<span>Ctrl + Enter</span>
						to save
						<span>Esc</span>
						to close
					</div>
				</div>

				<div class="modal-footer">
					<button
						type="button"
						class="cancel-button"
						onclick={closeNoteModal}
						disabled={saving}
					>
						Cancel
					</button>

					<button
						type="button"
						class="save-button"
						onclick={saveNote}
						disabled={!canSaveNote}
					>
						{#if saving}
							<span class="button-spinner"></span>
							Saving...
						{:else}
							{editingNote
								? 'Update Note'
								: 'Save Note'}
						{/if}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- =====================================================
	     DELETE MODAL
	====================================================== -->

	{#if showDeleteModal && noteToDelete}
		<div
			class="modal-backdrop"
			role="presentation"
			onclick={(event) => {
				if (event.target === event.currentTarget) {
					closeDeleteModal();
				}
			}}
		>
			<div
				class="modal delete-modal"
				role="dialog"
				aria-modal="true"
				aria-labelledby="delete-modal-title"
				tabindex="-1"
			>
				<div class="delete-content">
					<div class="delete-icon">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<polyline points="3 6 5 6 21 6" />
							<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
							<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
						</svg>
					</div>

					<h2 id="delete-modal-title">
						Delete this note?
					</h2>

					<p>
						Are you sure you want to delete
						<strong>
							"{noteToDelete.title}"
						</strong>?
					</p>

					<span class="delete-warning">
						This action cannot be undone.
					</span>
				</div>

				<div class="modal-footer">
					<button
						type="button"
						class="cancel-button"
						onclick={closeDeleteModal}
						disabled={deleting}
					>
						Cancel
					</button>

					<button
						type="button"
						class="danger-button"
						onclick={confirmDelete}
						disabled={deleting}
					>
						{#if deleting}
							<span class="button-spinner"></span>
							Deleting...
						{:else}
							Delete Note
						{/if}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- =====================================================
	     PASSWORD MODAL
	====================================================== -->

	{#if showPasswordModal}
		<div
			class="modal-backdrop"
			role="presentation"
			onclick={(event) => {
				if (event.target === event.currentTarget) {
					closePasswordModal();
				}
			}}
		>
			<div
				class="modal password-modal"
				role="dialog"
				aria-modal="true"
				aria-labelledby="password-modal-title"
				tabindex="-1"
			>
				<div class="modal-header">
					<div class="modal-header-icon">
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<rect
								x="3"
								y="11"
								width="18"
								height="10"
								rx="2"
							/>
							<path d="M7 11V7a5 5 0 0 1 10 0v4" />
						</svg>
					</div>

					<div class="modal-title-area">
						<h2 id="password-modal-title">
							Change Password
						</h2>

						<p>
							Use a new password for your local account.
						</p>
					</div>

					<button
						type="button"
						class="modal-close"
						onclick={closePasswordModal}
						aria-label="Close"
					>
						×
					</button>
				</div>

				<div class="modal-body">
					{#if passwordError}
						<div class="password-message error">
							<span>!</span>
							{passwordError}
						</div>
					{/if}

					<div class="form-group">
						<label for="current-password">
							Current Password
						</label>

						<div class="password-input">
							<input
								id="current-password"
								type={showCurrentPassword
									? 'text'
									: 'password'}
								bind:value={currentPassword}
								placeholder="Enter current password"
								autocomplete="current-password"
								disabled={passwordSaving}
							/>

							<button
								type="button"
								class="eye-button"
								onclick={() =>
									(showCurrentPassword =
										!showCurrentPassword)}
								aria-label="Toggle current password visibility"
							>
								{showCurrentPassword ? 'Hide' : 'Show'}
							</button>
						</div>
					</div>

					<div class="form-group">
						<label for="new-password">
							New Password
						</label>

						<div class="password-input">
							<input
								id="new-password"
								type={showNewPassword
									? 'text'
									: 'password'}
								bind:value={newPassword}
								placeholder="Minimum 6 characters"
								autocomplete="new-password"
								disabled={passwordSaving}
							/>

							<button
								type="button"
								class="eye-button"
								onclick={() =>
									(showNewPassword =
										!showNewPassword)}
								aria-label="Toggle new password visibility"
							>
								{showNewPassword ? 'Hide' : 'Show'}
							</button>
						</div>
					</div>

					<div class="form-group">
						<label for="confirm-password">
							Confirm New Password
						</label>

						<div class="password-input">
							<input
								id="confirm-password"
								type={showConfirmPassword
									? 'text'
									: 'password'}
								bind:value={confirmPassword}
								placeholder="Enter new password again"
								autocomplete="new-password"
								disabled={passwordSaving}
							/>

							<button
								type="button"
								class="eye-button"
								onclick={() =>
									(showConfirmPassword =
										!showConfirmPassword)}
								aria-label="Toggle confirm password visibility"
							>
								{showConfirmPassword ? 'Hide' : 'Show'}
							</button>
						</div>
					</div>

					<div class="password-rules">
						<div class:valid={passwordLongEnough}>
							<span>
								{passwordLongEnough ? '✓' : '•'}
							</span>
							At least 6 characters
						</div>

						<div class:valid={passwordChanged}>
							<span>
								{passwordChanged ? '✓' : '•'}
							</span>
							Different from current password
						</div>

						<div class:valid={passwordsMatch}>
							<span>
								{passwordsMatch ? '✓' : '•'}
							</span>
							Passwords match
						</div>
					</div>
				</div>

				<div class="modal-footer">
					<button
						type="button"
						class="cancel-button"
						onclick={closePasswordModal}
						disabled={passwordSaving}
					>
						Cancel
					</button>

					<button
						type="button"
						class="save-button"
						onclick={handleChangePassword}
						disabled={passwordSaving}
					>
						{#if passwordSaving}
							<span class="button-spinner"></span>
							Changing...
						{:else}
							Change Password
						{/if}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- =====================================================
	     TOAST
	====================================================== -->

	{#if toast.show}
		<div
			class:error-toast={toast.type === 'error'}
			class="toast"
			role="status"
		>
			<div class="toast-icon">
				{toast.type === 'error' ? '!' : '✓'}
			</div>

			<span>
				{toast.message}
			</span>

			<button
				type="button"
				onclick={closeToast}
				aria-label="Close notification"
			>
				×
			</button>
		</div>
	{/if}
</div>

<style>
	:global(*) {
		box-sizing: border-box;
	}

	:global(html),
	:global(body) {
		margin: 0;
		min-height: 100%;
		background: #06090f;
	}

	:global(body) {
		font-family:
			Inter,
			-apple-system,
			BlinkMacSystemFont,
			"Segoe UI",
			Roboto,
			Helvetica,
			Arial,
			sans-serif;
		color: #f5f5f7;
		-webkit-font-smoothing: antialiased;
	}

	:global(button),
	:global(input),
	:global(textarea) {
		font: inherit;
	}

	:global(button:focus-visible),
	:global(input:focus-visible),
	:global(textarea:focus-visible) {
		outline: 2px solid rgba(255, 90, 31, 0.85);
		outline-offset: 2px;
	}

	.notes-app {
		min-height: 100vh;
		background:
			radial-gradient(
				circle at 78% -5%,
				rgba(255, 90, 31, 0.055),
				transparent 30%
			),
			#06090f;
	}

	/* =====================================================
	   MOBILE TOP BAR
	====================================================== */

	.mobile-topbar {
		display: none;
	}

	.mobile-overlay {
		display: none;
	}

	/* =====================================================
	   SIDEBAR
	====================================================== */

	.sidebar {
		position: fixed;
		inset: 0 auto 0 0;
		width: 292px;
		padding: 30px 18px 20px;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		background: rgba(18, 18, 26, 0.98);
		border-right: 1px solid #292933;
		z-index: 50;
	}

	.sidebar-top {
		display: flex;
		flex-direction: column;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 3px 10px;
		margin-bottom: 40px;
	}

	.brand-icon {
		width: 39px;
		height: 39px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 11px;
		background: linear-gradient(
			135deg,
			#ff6a2a,
			#e84812
		);
		color: white;
		box-shadow:
			0 9px 25px rgba(255, 90, 31, 0.22);
	}

	.brand-icon svg {
		width: 20px;
		height: 20px;
	}

	.brand-icon.compact {
		width: 34px;
		height: 34px;
		border-radius: 9px;
	}

	.brand-icon.compact svg {
		width: 18px;
		height: 18px;
	}

	.brand-name {
		color: white;
		font-size: 16px;
		font-weight: 750;
		letter-spacing: -0.2px;
	}

	.brand-subtitle {
		margin-top: 2px;
		color: #70707e;
		font-size: 10px;
	}

	.sidebar-section {
		margin-bottom: 18px;
	}

	.section-label {
		padding: 0 12px;
		margin-bottom: 9px;
		color: #666673;
		font-size: 10px;
		font-weight: 750;
		letter-spacing: 0.8px;
		text-transform: uppercase;
	}

	.nav-item {
		width: 100%;
		height: 45px;
		display: flex;
		align-items: center;
		gap: 11px;
		padding: 0 12px;
		border: 1px solid transparent;
		border-radius: 10px;
		background: transparent;
		color: #9999a7;
		cursor: pointer;
		text-align: left;
		font-size: 13px;
		font-weight: 600;
		transition: 0.18s ease;
	}

	.nav-item:hover {
		background: #20202a;
		color: white;
	}

	.nav-item.active {
		background: rgba(255, 90, 31, 0.10);
		border-color: rgba(255, 90, 31, 0.28);
		color: white;
	}

	.nav-item-icon {
		width: 19px;
		height: 19px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.nav-item-icon svg {
		width: 17px;
		height: 17px;
	}

	.nav-count {
		margin-left: auto;
		min-width: 24px;
		height: 22px;
		padding: 0 7px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 6px;
		background: #6f2818;
		color: #ffd9ca;
		font-size: 10px;
		font-weight: 700;
	}

	.new-sidebar-button {
		width: 100%;
		height: 43px;
		margin-top: 7px;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		border: 0;
		border-radius: 9px;
		background: linear-gradient(
			135deg,
			#ff5a1f,
			#e84812
		);
		color: white;
		font-size: 13px;
		font-weight: 650;
		cursor: pointer;
		box-shadow:
			0 9px 24px rgba(255, 90, 31, 0.18);
		transition:
			transform 0.18s ease,
			box-shadow 0.18s ease,
			filter 0.18s ease;
	}

	.new-sidebar-button svg {
		width: 17px;
		height: 17px;
	}

	.new-sidebar-button:hover {
		transform: translateY(-1px);
		filter: brightness(1.08);
		box-shadow:
			0 12px 30px rgba(255, 90, 31, 0.28);
	}

	.sidebar-bottom {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	.user-card {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 13px 9px;
		margin-bottom: 9px;
		border-top: 1px solid #292933;
		border-bottom: 1px solid #292933;
	}

	.user-avatar {
		width: 36px;
		height: 36px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: linear-gradient(
			135deg,
			#ff6a2a,
			#e84812
		);
		color: white;
		font-size: 13px;
		font-weight: 750;
	}

	.user-details {
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.user-label {
		color: #5e5e6b;
		font-size: 8px;
		font-weight: 750;
		letter-spacing: 0.7px;
	}

	.user-email {
		max-width: 170px;
		color: #c8c8d1;
		font-size: 11px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.provider-badge {
		color: #6f6f7d;
		font-size: 9px;
	}

	.sidebar-action,
	.google-password-info {
		width: 100%;
		min-height: 41px;
		display: flex;
		align-items: center;
		gap: 11px;
		padding: 0 11px;
		border: 0;
		border-radius: 8px;
		background: transparent;
		color: #888894;
		text-align: left;
		font-size: 12px;
		font-weight: 600;
	}

	.sidebar-action {
		cursor: pointer;
		transition: 0.16s ease;
	}

	.sidebar-action:hover {
		background: #20202a;
		color: #eeeeF2;
	}

	.sidebar-action.logout:hover {
		background: rgba(220, 70, 91, 0.09);
		color: #ff8d9d;
	}

	.google-password-info {
		color: #686875;
		font-size: 10px;
		line-height: 1.35;
	}

	.sidebar-action-icon {
		width: 18px;
		height: 18px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.sidebar-action-icon svg {
		width: 16px;
		height: 16px;
	}

	/* =====================================================
	   MAIN
	====================================================== */

	.main-content {
		margin-left: 292px;
		min-height: 100vh;
		padding: 52px 52px 72px;
	}

	.content-container {
		width: 100%;
		max-width: 1240px;
		margin: 0 auto;
	}

	.top-header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 30px;
		margin-bottom: 30px;
	}

	.eyebrow {
		margin-bottom: 8px;
		color: #ff6a2a;
		font-size: 10px;
		font-weight: 800;
		letter-spacing: 1.2px;
	}

	.top-header h1 {
		margin: 0 0 7px;
		color: white;
		font-size: 38px;
		line-height: 1.15;
		font-weight: 760;
		letter-spacing: -1px;
	}

	.top-header p {
		max-width: 620px;
		margin: 0;
		color: #858593;
		font-size: 14px;
		line-height: 1.6;
	}

	.new-note-button {
		height: 44px;
		flex-shrink: 0;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		padding: 0 18px;
		border: 0;
		border-radius: 9px;
		background: linear-gradient(
			135deg,
			#ff5a1f,
			#e84812
		);
		color: white;
		font-size: 13px;
		font-weight: 650;
		cursor: pointer;
		box-shadow:
			0 8px 24px rgba(255, 90, 31, 0.18);
		transition:
			transform 0.18s ease,
			box-shadow 0.18s ease,
			filter 0.18s ease;
	}

	.new-note-button svg {
		width: 17px;
		height: 17px;
	}

	.new-note-button:hover {
		transform: translateY(-1px);
		filter: brightness(1.08);
		box-shadow:
			0 12px 29px rgba(255, 90, 31, 0.26);
	}

	.stats-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 14px;
		margin-bottom: 32px;
	}

	.stat-card {
		min-height: 98px;
		display: flex;
		align-items: center;
		gap: 13px;
		padding: 18px 20px;
		background: #15151d;
		border: 1px solid #292933;
		border-radius: 12px;
		transition:
			transform 0.18s ease,
			border-color 0.18s ease,
			background 0.18s ease;
	}

	.stat-card:hover {
		transform: translateY(-1px);
		border-color: #383845;
		background: #171720;
	}

	.stat-icon {
		width: 40px;
		height: 40px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 10px;
	}

	.stat-icon svg {
		width: 19px;
		height: 19px;
	}

	.stat-icon.purple {
		background: rgba(255, 90, 31, 0.12);
		color: #ff8d66;
	}

	.stat-icon.blue {
		background: rgba(63, 134, 255, 0.12);
		color: #79adff;
	}

	.stat-icon.green {
		background: rgba(58, 180, 112, 0.11);
		color: #73d49b;
	}

	.stat-content {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.stat-label {
		color: #737381;
		font-size: 10px;
		font-weight: 600;
	}

	.stat-value {
		color: #eeeeF3;
		font-size: 14px;
		font-weight: 700;
	}

	.stat-value.protected {
		color: #8ad9a7;
	}

	/* =====================================================
	   NOTES TOOLBAR
	====================================================== */

	.notes-section {
		min-width: 0;
	}

	.toolbar {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 24px;
		margin-bottom: 18px;
	}

	.toolbar-title {
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.toolbar-title h2 {
		margin: 0 0 3px;
		color: #eeeeF3;
		font-size: 17px;
		font-weight: 700;
		letter-spacing: -0.2px;
	}

	.toolbar-title p {
		margin: 0;
		color: #686875;
		font-size: 10px;
		line-height: 1.4;
	}

	.result-count {
		flex-shrink: 0;
		padding: 4px 8px;
		border-radius: 5px;
		background: #1c1c25;
		color: #888895;
		font-size: 10px;
		font-weight: 650;
	}

	.search-container {
		position: relative;
		width: 320px;
		flex-shrink: 0;
	}

	.search-container input {
		width: 100%;
		height: 42px;
		padding: 0 74px 0 40px;
		border: 1px solid #30303a;
		border-radius: 9px;
		background: #14141b;
		color: #f4f4f6;
		outline: none;
		font-size: 12px;
		transition: 0.16s ease;
	}

	.search-container input::placeholder {
		color: #62626e;
	}

	.search-container input:focus {
		border-color: #ff5a1f;
		background: #16161e;
		box-shadow:
			0 0 0 3px rgba(255, 90, 31, 0.10);
	}

	.search-svg {
		position: absolute;
		left: 13px;
		top: 50%;
		width: 16px;
		height: 16px;
		transform: translateY(-50%);
		color: #6b6b78;
		pointer-events: none;
	}

	.search-shortcut {
		position: absolute;
		right: 11px;
		top: 50%;
		transform: translateY(-50%);
		padding: 3px 5px;
		border: 1px solid #30303a;
		border-radius: 5px;
		color: #5f5f6b;
		font-size: 8px;
		pointer-events: none;
	}

	.search-container:has(.clear-search) .search-shortcut {
		display: none;
	}

	.clear-search {
		position: absolute;
		right: 8px;
		top: 50%;
		width: 25px;
		height: 25px;
		transform: translateY(-50%);
		border: 0;
		border-radius: 6px;
		background: transparent;
		color: #81818d;
		font-size: 18px;
		line-height: 1;
		cursor: pointer;
	}

	.clear-search:hover {
		background: #272730;
		color: white;
	}

	/* =====================================================
	   ERROR
	====================================================== */

	.error-message {
		display: flex;
		align-items: center;
		gap: 11px;
		padding: 12px 14px;
		margin-bottom: 18px;
		border: 1px solid #67303a;
		border-radius: 9px;
		background: rgba(96, 28, 42, 0.25);
	}

	.error-icon {
		width: 25px;
		height: 25px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: #6c2b37;
		color: #ffadb9;
		font-size: 12px;
		font-weight: 800;
	}

	.error-text {
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.error-text strong {
		color: #ffadb8;
		font-size: 12px;
	}

	.error-text span {
		color: #c87883;
		font-size: 11px;
	}

	.error-close {
		margin-left: auto;
		border: 0;
		background: transparent;
		color: #c87883;
		font-size: 19px;
		cursor: pointer;
	}

	/* =====================================================
	   NOTE CARDS
	====================================================== */

	.notes-grid {
		display: grid;
		grid-template-columns:
			repeat(3, minmax(0, 1fr));
		gap: 16px;
	}

	.note-card {
		position: relative;
		min-height: 228px;
		display: flex;
		flex-direction: column;
		padding: 20px 20px 18px 22px;
		border: 1px solid #252c36;
		border-left: 2px solid var(--note-accent, #ff5a1f);
		border-radius: 12px;
		background: linear-gradient(145deg, #0c1118, #0a0f16);
		overflow: hidden;
		transition:
			transform 0.18s ease,
			border-color 0.18s ease,
			background 0.18s ease,
			box-shadow 0.18s ease;
	}

	.note-card.ideas { --note-accent: #ff8a24; --note-soft: rgba(255, 138, 36, 0.10); --note-text: #ffb36b; }
	.note-card.study { --note-accent: #3b9cff; --note-soft: rgba(59, 156, 255, 0.10); --note-text: #76b9ff; }
	.note-card.travel { --note-accent: #25c4c0; --note-soft: rgba(37, 196, 192, 0.10); --note-text: #5ee4df; }
	.note-card.health { --note-accent: #31c777; --note-soft: rgba(49, 199, 119, 0.10); --note-text: #6ee3a0; }
	.note-card.work { --note-accent: #8b6cff; --note-soft: rgba(139, 108, 255, 0.10); --note-text: #b09cff; }
	.note-card.personal { --note-accent: #ff4964; --note-soft: rgba(255, 73, 100, 0.10); --note-text: #ff8296; }

	.note-card:hover {
		transform: translateY(-3px);
		border-color: color-mix(in srgb, var(--note-accent) 45%, #252c36);
		background: #0f151e;
		box-shadow:
			0 16px 34px rgba(0, 0, 0, 0.2),
			0 0 0 1px rgba(255, 90, 31, 0.04);
	}

	.note-card-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 15px;
	}

	.note-category {
		padding: 4px 7px;
		border-radius: 5px;
		background: var(--note-soft);
		color: var(--note-text);
		font-size: 8px;
		font-weight: 800;
		letter-spacing: 0.8px;
	}

	.note-actions {
		display: flex;
		gap: 3px;
		opacity: 0.72;
		transition: opacity 0.18s ease;
	}

	.note-card:hover .note-actions {
		opacity: 1;
	}

	.icon-button {
		width: 29px;
		height: 29px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 0;
		border-radius: 7px;
		background: transparent;
		cursor: pointer;
		transition: 0.15s ease;
	}

	.icon-button svg {
		width: 14px;
		height: 14px;
	}

	.icon-button.edit {
		color: #aeb7c4;
	}

	.icon-button.edit:hover {
		background: #202833;
		color: #ffffff;
	}

	.icon-button.delete {
		color: #7a575e;
	}

	.icon-button.delete:hover {
		background: #352128;
		color: #f28a9b;
	}

	.note-card-content {
		flex: 1;
		min-width: 0;
	}

	.note-card h3 {
		margin: 0 0 9px;
		color: #f0f0f4;
		font-size: 16px;
		line-height: 1.35;
		font-weight: 680;
		letter-spacing: -0.2px;
		word-break: break-word;
	}

	.note-card p {
		margin: 0;
		color: #8f8f9c;
		font-size: 12px;
		line-height: 1.7;
		white-space: pre-wrap;
		display: -webkit-box;
		-webkit-line-clamp: 5;
		-webkit-box-orient: vertical;
		overflow: hidden;
		word-break: break-word;
	}

	.note-footer {
		display: flex;
		align-items: center;
		padding-top: 13px;
		margin-top: 18px;
		border-top: 1px solid #26262f;
	}

	.note-date {
		display: flex;
		align-items: center;
		gap: 6px;
		color: #676773;
		font-size: 9px;
		font-weight: 550;
	}

	.note-date svg {
		width: 12px;
		height: 12px;
	}

	/* =====================================================
	   SKELETONS
	====================================================== */

	.skeleton-card {
		pointer-events: none;
	}

	.skeleton {
		position: relative;
		overflow: hidden;
		background: #24242d;
		border-radius: 6px;
	}

	.skeleton::after {
		content: "";
		position: absolute;
		inset: 0;
		transform: translateX(-100%);
		background: linear-gradient(
			90deg,
			transparent,
			rgba(255, 255, 255, 0.04),
			transparent
		);
		animation: shimmer 1.35s infinite;
	}

	@keyframes shimmer {
		100% {
			transform: translateX(100%);
		}
	}

	.skeleton-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 20px;
	}

	.skeleton-badge {
		width: 42px;
		height: 18px;
	}

	.skeleton-actions {
		display: flex;
		gap: 6px;
	}

	.skeleton-circle {
		width: 27px;
		height: 27px;
		border-radius: 7px;
	}

	.skeleton-title {
		width: 62%;
		height: 17px;
		margin-bottom: 15px;
	}

	.skeleton-line {
		width: 92%;
		height: 10px;
		margin-bottom: 9px;
	}

	.skeleton-line.short {
		width: 63%;
	}

	.skeleton-footer {
		margin-top: auto;
		padding-top: 18px;
		border-top: 1px solid #26262f;
	}

	.skeleton-date {
		width: 95px;
		height: 10px;
	}

	/* =====================================================
	   EMPTY
	====================================================== */

	.empty-state {
		min-height: 400px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 50px 20px;
		text-align: center;
		border: 1px dashed #2a2a34;
		border-radius: 12px;
		background: rgba(20, 20, 27, 0.42);
	}

	.empty-icon {
		width: 64px;
		height: 64px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 17px;
		border-radius: 16px;
		background: #181820;
		color: #ff6a2a;
	}

	.empty-icon svg {
		width: 29px;
		height: 29px;
	}

	.empty-state h2 {
		margin: 0 0 7px;
		color: #eeeeF2;
		font-size: 20px;
		font-weight: 700;
	}

	.empty-state p {
		max-width: 390px;
		margin: 0 0 22px;
		color: #777783;
		font-size: 12px;
		line-height: 1.6;
	}

	.empty-state strong {
		color: #b7b7c2;
	}

	.empty-button {
		height: 42px;
	}

	.secondary-button {
		height: 39px;
		padding: 0 15px;
		border: 1px solid #33333d;
		border-radius: 8px;
		background: #1a1a22;
		color: #c9c9d2;
		font-size: 12px;
		font-weight: 600;
		cursor: pointer;
	}

	.secondary-button:hover {
		background: #24242d;
		color: white;
	}

	/* =====================================================
	   MODALS
	====================================================== */

	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 100;
		padding: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.75);
		backdrop-filter: blur(6px);
		animation: fadeIn 0.16s ease;
	}

	.modal {
		width: min(560px, 100%);
		max-height: calc(100vh - 40px);
		overflow: auto;
		border: 1px solid #373742;
		border-radius: 14px;
		background: #191920;
		box-shadow:
			0 30px 90px rgba(0, 0, 0, 0.55);
		animation: modalIn 0.18s ease;
	}

	.note-modal {
		width: min(620px, 100%);
	}

	.password-modal {
		width: min(520px, 100%);
	}

	.delete-modal {
		width: min(440px, 100%);
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}

		to {
			opacity: 1;
		}
	}

	@keyframes modalIn {
		from {
			opacity: 0;
			transform: translateY(8px) scale(0.985);
		}

		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.modal-header {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding: 20px 21px 17px;
		border-bottom: 1px solid #2b2b35;
	}

	.modal-header-icon {
		width: 36px;
		height: 36px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 9px;
		background: rgba(255, 90, 31, 0.12);
		color: #ff8a5c;
	}

	.modal-header-icon svg {
		width: 18px;
		height: 18px;
	}

	.modal-title-area {
		flex: 1;
		min-width: 0;
	}

	.modal-title-area h2 {
		margin: 0 0 4px;
		color: #f2f2f5;
		font-size: 17px;
		font-weight: 700;
	}

	.modal-title-area p {
		margin: 0;
		color: #777783;
		font-size: 11px;
		line-height: 1.5;
	}

	.modal-close {
		width: 30px;
		height: 30px;
		flex-shrink: 0;
		border: 0;
		border-radius: 7px;
		background: transparent;
		color: #7e7e8b;
		font-size: 22px;
		line-height: 1;
		cursor: pointer;
	}

	.modal-close:hover {
		background: #292932;
		color: white;
	}

	.modal-body {
		padding: 21px;
	}

	.form-group {
		margin-bottom: 18px;
	}

	.form-group:last-child {
		margin-bottom: 0;
	}

	.form-group label {
		display: block;
		margin-bottom: 7px;
		color: #d8d8e0;
		font-size: 11px;
		font-weight: 650;
	}

	.label-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}

	.label-row span {
		color: #62626e;
		font-size: 9px;
	}

	.label-row span.counter-warning {
		color: #ff8d9d;
	}

	.modal-body input,
	.modal-body textarea {
		width: 100%;
		border: 1px solid #34343e;
		border-radius: 8px;
		background: #111118;
		color: #f3f3f6;
		outline: none;
		font-size: 12px;
		transition: 0.16s ease;
	}

	.modal-body input {
		height: 43px;
		padding: 0 12px;
	}

	.modal-body textarea {
		min-height: 190px;
		padding: 12px;
		resize: vertical;
		line-height: 1.65;
	}

	.modal-body input::placeholder,
	.modal-body textarea::placeholder {
		color: #5d5d68;
	}

	.modal-body input:focus,
	.modal-body textarea:focus {
		border-color: #ff5a1f;
		background: #13131a;
		box-shadow:
			0 0 0 3px rgba(255, 90, 31, 0.09);
	}

	.password-input {
		position: relative;
	}

	.password-input input {
		padding-right: 60px;
	}

	.eye-button {
		position: absolute;
		right: 8px;
		top: 50%;
		transform: translateY(-50%);
		border: 0;
		background: transparent;
		color: #777783;
		font-size: 9px;
		font-weight: 650;
		cursor: pointer;
	}

	.eye-button:hover {
		color: white;
	}

	.password-message {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 11px;
		margin-bottom: 17px;
		border: 1px solid #66303a;
		border-radius: 8px;
		background: rgba(96, 28, 42, 0.25);
		color: #ffabb7;
		font-size: 11px;
	}

	.password-message span {
		width: 19px;
		height: 19px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: #632d38;
		font-weight: 800;
	}

	.password-rules {
		display: grid;
		gap: 6px;
		padding: 12px;
		border: 1px solid #292933;
		border-radius: 8px;
		background: #15151c;
	}

	.password-rules div {
		display: flex;
		align-items: center;
		gap: 7px;
		color: #6f6f7b;
		font-size: 10px;
	}

	.password-rules div.valid {
		color: #7fd19e;
	}

	.password-rules span {
		width: 13px;
		text-align: center;
	}

	.keyboard-tip {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 6px;
		color: #5f5f6b;
		font-size: 9px;
	}

	.keyboard-tip span {
		padding: 3px 5px;
		border: 1px solid #30303a;
		border-radius: 5px;
		background: #15151c;
		color: #777783;
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 9px;
		padding: 15px 21px 19px;
		border-top: 1px solid #292932;
	}

	.cancel-button,
	.save-button,
	.danger-button {
		height: 40px;
		padding: 0 16px;
		border-radius: 8px;
		font-size: 11px;
		font-weight: 650;
		cursor: pointer;
	}

	.cancel-button {
		border: 1px solid #35353f;
		background: #1d1d24;
		color: #aaaab5;
	}

	.cancel-button:hover:not(:disabled) {
		background: #282830;
		color: white;
	}

	.save-button {
		min-width: 108px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 7px;
		border: 0;
		background: #ff5a1f;
		color: white;
	}

	.save-button:hover:not(:disabled) {
		background: #ff5a1f;
	}

	.danger-button {
		min-width: 108px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 7px;
		border: 0;
		background: #b33c50;
		color: white;
	}

	.danger-button:hover:not(:disabled) {
		background: #c8485d;
	}

	.save-button:disabled,
	.cancel-button:disabled,
	.danger-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.button-spinner {
		width: 12px;
		height: 12px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.delete-content {
		padding: 28px 24px 22px;
		text-align: center;
	}

	.delete-icon {
		width: 48px;
		height: 48px;
		margin: 0 auto 15px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 12px;
		background: rgba(190, 59, 80, 0.13);
		color: #ef8293;
	}

	.delete-icon svg {
		width: 21px;
		height: 21px;
	}

	.delete-content h2 {
		margin: 0 0 9px;
		color: #f1f1f4;
		font-size: 18px;
	}

	.delete-content p {
		margin: 0 0 8px;
		color: #898995;
		font-size: 12px;
		line-height: 1.6;
	}

	.delete-content strong {
		color: #d6d6de;
	}

	.delete-warning {
		color: #69545a;
		font-size: 10px;
	}

	/* =====================================================
	   TOAST
	====================================================== */

	.toast {
		position: fixed;
		right: 24px;
		bottom: 24px;
		z-index: 200;
		min-width: 280px;
		max-width: min(380px, calc(100vw - 32px));
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 13px;
		border: 1px solid #2d6744;
		border-radius: 10px;
		background: #14251a;
		color: #b8e8c9;
		box-shadow:
			0 16px 40px rgba(0, 0, 0, 0.35);
		font-size: 11px;
		animation: toastIn 0.22s ease;
	}

	.toast.error-toast {
		border-color: #71303d;
		background: #2b171d;
		color: #ffacb8;
	}

	.toast-icon {
		width: 24px;
		height: 24px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: rgba(83, 181, 121, 0.15);
		font-weight: 800;
	}

	.error-toast .toast-icon {
		background: rgba(222, 75, 97, 0.15);
	}

	.toast > span {
		flex: 1;
	}

	.toast button {
		border: 0;
		background: transparent;
		color: inherit;
		font-size: 18px;
		cursor: pointer;
		opacity: 0.7;
	}

	@keyframes toastIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}

		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* =====================================================
	   RESPONSIVE
	====================================================== */

	@media (max-width: 1100px) {
		.main-content {
			padding: 42px 30px 60px;
		}

		.notes-grid {
			grid-template-columns:
				repeat(2, minmax(0, 1fr));
		}
	}

	@media (max-width: 820px) {
		.sidebar {
			width: 230px;
		}

		.main-content {
			margin-left: 230px;
			padding: 35px 25px 50px;
		}

		.stats-row {
			grid-template-columns: 1fr;
		}

		.toolbar {
			align-items: stretch;
			flex-direction: column;
			gap: 12px;
		}

		.search-container {
			width: 100%;
		}

		.user-email {
			max-width: 130px;
		}
	}

	@media (max-width: 650px) {
		.mobile-topbar {
			position: sticky;
			top: 0;
			z-index: 70;
			height: 62px;
			padding: 0 15px;
			display: flex;
			align-items: center;
			justify-content: space-between;
			background: rgba(17, 17, 24, 0.96);
			border-bottom: 1px solid #292933;
			backdrop-filter: blur(12px);
		}

		.mobile-brand {
			display: flex;
			align-items: center;
			gap: 9px;
			color: white;
			font-size: 14px;
			font-weight: 700;
		}

		.mobile-actions {
			display: flex;
			align-items: center;
			gap: 7px;
		}

		.mobile-create,
		.mobile-menu-button {
			width: 36px;
			height: 36px;
			display: flex;
			align-items: center;
			justify-content: center;
			border: 1px solid #30303a;
			border-radius: 9px;
			background: #181820;
			color: #dadae2;
			cursor: pointer;
		}

		.mobile-create {
			border-color: transparent;
			background: #ff5a1f;
			color: white;
			font-size: 19px;
		}

		.mobile-menu-button svg {
			width: 18px;
			height: 18px;
		}

		.mobile-overlay {
			position: fixed;
			inset: 62px 0 0;
			z-index: 55;
			display: block;
			border: 0;
			background: rgba(0, 0, 0, 0.5);
			backdrop-filter: blur(2px);
		}

		.sidebar {
			position: fixed;
			top: 62px;
			left: 0;
			bottom: 0;
			width: min(290px, 86vw);
			padding: 20px 16px 18px;
			transform: translateX(-105%);
			transition: transform 0.22s ease;
			z-index: 60;
			box-shadow:
				18px 0 45px rgba(0, 0, 0, 0.32);
		}

		.sidebar.mobile-open {
			transform: translateX(0);
		}

		.brand {
			display: none;
		}

		.main-content {
			margin-left: 0;
			padding: 28px 16px 45px;
		}

		.top-header {
			align-items: stretch;
			flex-direction: column;
			gap: 17px;
		}

		.top-header h1 {
			font-size: 29px;
		}

		.top-header .new-note-button {
			display: none;
		}

		.stats-row {
			margin-bottom: 28px;
		}

		.notes-grid {
			grid-template-columns: 1fr;
		}

		.toolbar-title {
			align-items: flex-start;
			justify-content: space-between;
		}

		.search-shortcut {
			display: none;
		}

		.search-container input {
			padding-right: 40px;
		}

		.toast {
			right: 16px;
			bottom: 16px;
			left: 16px;
			min-width: 0;
			max-width: none;
		}
	}

	@media (max-width: 420px) {
		.main-content {
			padding: 24px 13px 35px;
		}

		.top-header h1 {
			font-size: 27px;
		}

		.stat-card {
			padding: 13px;
		}

		.note-card {
			min-height: 205px;
		}

		.modal-backdrop {
			padding: 10px;
		}

		.modal-header,
		.modal-body {
			padding: 17px;
		}

		.modal-footer {
			padding: 13px 17px 17px;
		}

		.keyboard-tip {
			display: none;
		}
	}
</style>
