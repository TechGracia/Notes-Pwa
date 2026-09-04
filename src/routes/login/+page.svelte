<script>
    import { onMount } from 'svelte';

    import {
        loginUser,
        createUser,
        forgotPassword,
        getCurrentUser
    } from '$lib/api.js';

    let email = $state('');
    let password = $state('');

    let loading = $state(false);
    let googleLoading = $state(false);

    let error = $state('');
    let success = $state('');

    let isRegisterMode = $state(false);
    let isForgotMode = $state(false);

    let newPassword = $state('');
    let confirmPassword = $state('');

    let showPassword = $state(false);
    let showNewPassword = $state(false);
    let showConfirmPassword = $state(false);


    // =========================================================
    // PAGE LOAD
    // =========================================================

    onMount(async () => {

        const urlParams = new URLSearchParams(
            window.location.search
        );


        // =====================================================
        // GOOGLE LOGIN SUCCESS
        // =====================================================

        const googleToken = urlParams.get('token');

        if (googleToken) {

            console.log(
                'Google JWT received on frontend.'
            );

            // IMPORTANT:
            // api.js uses sessionStorage.
            // Therefore Google JWT MUST also use sessionStorage.

            sessionStorage.setItem(
                'access_token',
                googleToken
            );


            // Remove token from URL immediately.
            // This prevents the JWT from remaining visible
            // in the browser address bar.

            window.history.replaceState(
                {},
                document.title,
                '/login'
            );


            try {

                console.log(
                    'Validating Google JWT with /me...'
                );

                const user = await getCurrentUser();

                console.log(
                    'Google user authenticated:',
                    user
                );


                // Store useful user information.

                if (user?.email) {
                    sessionStorage.setItem(
                        'user_email',
                        user.email
                    );
                }

                if (user?.id) {
                    sessionStorage.setItem(
                        'user_id',
                        String(user.id)
                    );
                }


                // Google login completely successful.

                console.log(
                    'Google login successful. Redirecting to dashboard...'
                );

                window.location.replace('/');

            } catch (err) {

                console.error(
                    'Google JWT validation failed:',
                    err
                );


                // Remove invalid token.

                sessionStorage.removeItem(
                    'access_token'
                );

                sessionStorage.removeItem(
                    'user_email'
                );

                sessionStorage.removeItem(
                    'user_id'
                );


                error =
                    'Google login succeeded, but the session could not be validated.';
            }

            return;
        }


        // =====================================================
        // GOOGLE LOGIN ERROR
        // =====================================================

        const googleError =
            urlParams.get('error');

        if (
            googleError ===
            'google_login_failed'
        ) {

            error =
                'Google login failed. Please try again.';

            window.history.replaceState(
                {},
                document.title,
                '/login'
            );

            return;
        }


        // =====================================================
        // CHECK EXISTING SESSION
        // =====================================================

        const token =
            sessionStorage.getItem(
                'access_token'
            );

        if (!token) {
            return;
        }


        try {

            const user =
                await getCurrentUser();


            if (user?.email) {
                sessionStorage.setItem(
                    'user_email',
                    user.email
                );
            }

            if (user?.id) {
                sessionStorage.setItem(
                    'user_id',
                    String(user.id)
                );
            }


            console.log(
                'Existing valid session found.'
            );

            window.location.replace('/');

        } catch (err) {

            console.log(
                'Stored session token is invalid or expired.'
            );

            sessionStorage.removeItem(
                'access_token'
            );

            sessionStorage.removeItem(
                'user_email'
            );

            sessionStorage.removeItem(
                'user_id'
            );
        }
    });


    // =========================================================
    // GOOGLE LOGIN
    // =========================================================

    function loginWithGoogle() {

        googleLoading = true;

        error = '';
        success = '';


        // Backend starts OAuth flow.

        window.location.href =
            'http://localhost:8000/auth/google';
    }


    // =========================================================
    // FORM SUBMIT
    // =========================================================

    async function handleSubmit(event) {

        event.preventDefault();

        error = '';
        success = '';


        const cleanEmail =
            email.trim().toLowerCase();


        // =====================================================
        // EMAIL VALIDATION
        // =====================================================

        if (!cleanEmail) {

            error =
                'Please enter your email.';

            return;
        }


        // =====================================================
        // FORGOT PASSWORD
        // =====================================================

        if (isForgotMode) {

            if (!newPassword) {

                error =
                    'Please enter a new password.';

                return;
            }


            if (newPassword.length < 6) {

                error =
                    'New password must be at least 6 characters.';

                return;
            }


            if (!confirmPassword) {

                error =
                    'Please confirm your new password.';

                return;
            }


            if (
                newPassword !==
                confirmPassword
            ) {

                error =
                    'New passwords do not match.';

                return;
            }


            loading = true;


            try {

                await forgotPassword(
                    cleanEmail,
                    newPassword
                );


                success =
                    'Password reset successfully. You can now log in.';


                isForgotMode = false;
                isRegisterMode = false;


                password = '';
                newPassword = '';
                confirmPassword = '';


                showPassword = false;
                showNewPassword = false;
                showConfirmPassword = false;

            } catch (err) {

                console.error(
                    'Password reset error:',
                    err
                );

                error =
                    err?.message ||
                    'Could not reset your password.';

            } finally {

                loading = false;
            }

            return;
        }


        // =====================================================
        // PASSWORD VALIDATION
        // =====================================================

        if (!password) {

            error =
                'Please enter your password.';

            return;
        }


        loading = true;


        try {


            // =================================================
            // REGISTER
            // =================================================

            if (isRegisterMode) {

                await createUser(
                    cleanEmail,
                    password
                );


                success =
                    'Account created successfully. You can now log in.';


                isRegisterMode = false;

                password = '';

                showPassword = false;

                return;
            }


            // =================================================
            // NORMAL LOGIN
            // =================================================

            const data =
                await loginUser(
                    cleanEmail,
                    password
                );


            if (
                !data ||
                !data.access_token
            ) {

                throw new Error(
                    'Login succeeded but no access token was received.'
                );
            }


            // loginUser() already stores the token
            // in sessionStorage.


            sessionStorage.setItem(
                'user_email',
                cleanEmail
            );


            // Validate the token before redirecting.

            const user =
                await getCurrentUser();


            if (user?.id) {

                sessionStorage.setItem(
                    'user_id',
                    String(user.id)
                );
            }


            console.log(
                'Normal login successful.'
            );


            window.location.replace('/');

        } catch (err) {

            console.error(
                'Login/Register error:',
                err
            );


            error =
                err?.message ||
                (
                    isRegisterMode
                        ? 'Could not create your account.'
                        : 'Invalid email or password.'
                );

        } finally {

            loading = false;
        }
    }


    // =========================================================
    // SWITCH LOGIN / REGISTER
    // =========================================================

    function switchMode() {

        isRegisterMode =
            !isRegisterMode;

        isForgotMode = false;

        error = '';
        success = '';

        password = '';

        newPassword = '';
        confirmPassword = '';

        showPassword = false;
        showNewPassword = false;
        showConfirmPassword = false;
    }


    // =========================================================
    // FORGOT PASSWORD MODE
    // =========================================================

    function showForgotPassword() {

        isForgotMode = true;

        isRegisterMode = false;

        error = '';
        success = '';

        password = '';

        newPassword = '';
        confirmPassword = '';

        showPassword = false;
    }


    // =========================================================
    // BACK TO LOGIN
    // =========================================================

    function backToLogin() {

        isForgotMode = false;

        isRegisterMode = false;

        error = '';
        success = '';

        password = '';

        newPassword = '';
        confirmPassword = '';

        showPassword = false;
        showNewPassword = false;
        showConfirmPassword = false;
    }


    // =========================================================
    // ESCAPE KEY
    // =========================================================

    function handleKeydown(event) {

        if (
            event.key === 'Escape' &&
            (
                isForgotMode ||
                isRegisterMode
            )
        ) {

            backToLogin();
        }
    }


    // =========================================================
    // PASSWORD STRENGTH
    // =========================================================

    function passwordStrength(value) {

        if (!value) {
            return 0;
        }


        let score = 0;


        if (value.length >= 6) {
            score += 1;
        }


        if (value.length >= 10) {
            score += 1;
        }


        if (
            /[A-Z]/.test(value) &&
            /[a-z]/.test(value)
        ) {

            score += 1;
        }


        if (/\d/.test(value)) {
            score += 1;
        }


        if (
            /[^A-Za-z0-9]/.test(value)
        ) {

            score += 1;
        }


        return Math.min(score, 4);
    }


    const strengthLabels = [
        '',
        'Basic',
        'Fair',
        'Good',
        'Strong'
    ];
</script>

<svelte:head>
    <title>
        {isForgotMode ? 'Reset Password' : isRegisterMode ? 'Create Account' : 'Login'} - Notes
    </title>
    <meta name="description" content="Secure notes application" />
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<div class="auth-page">
    <div class="ambient ambient-one"></div>
    <div class="ambient ambient-two"></div>

    <main class="auth-shell">
        <section class="intro-panel" aria-label="Notes introduction">
            <div class="brand">
                <div class="brand-icon" aria-hidden="true">
                    <svg viewBox="0 0 32 32" fill="none">
                        <rect x="7" y="3" width="18" height="24" rx="5" fill="currentColor" opacity=".2" />
                        <rect x="3" y="7" width="18" height="22" rx="5" fill="currentColor" />
                        <path d="M8.5 14h7.5M8.5 18h7.5M8.5 22h5" stroke="#fff" stroke-width="1.8" stroke-linecap="round" />
                    </svg>
                </div>
                <div>
                    <strong>Notes</strong>
                    <span>Personal workspace</span>
                </div>
            </div>

            <div class="intro-copy">
                <div class="eyebrow"><span></span> YOUR PRIVATE WORKSPACE</div>
                <h2>Ideas deserve<br /><em>a place of their own.</em></h2>
                <p>Capture thoughts, plans and important information in one secure space — simple, focused and always ready.</p>
            </div>

            <div class="feature-list">
                <div class="feature">
                    <div class="feature-icon orange">
                        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 4.5h10.5L19 8v11.5H5V4.5Z" stroke="currentColor" stroke-width="1.7"/><path d="M15 4.5V8h4M8 12h8M8 15.5h5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </div>
                    <div><strong>Keep everything together</strong><span>Your notes stay organized in one place.</span></div>
                </div>
                <div class="feature">
                    <div class="feature-icon green">
                        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.5 19 6v5.5c0 4.3-2.8 7.6-7 9-4.2-1.4-7-4.7-7-9V6l7-2.5Z" stroke="currentColor" stroke-width="1.7"/><path d="m9 12 2 2 4-4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </div>
                    <div><strong>Private by default</strong><span>Your account keeps your workspace protected.</span></div>
                </div>
            </div>

            <div class="intro-footer"><span class="status-dot"></span> Secure workspace</div>
        </section>

        <section class="auth-card">
            <div class="mobile-brand brand">
                <div class="brand-icon" aria-hidden="true">
                    <svg viewBox="0 0 32 32" fill="none"><rect x="7" y="3" width="18" height="24" rx="5" fill="currentColor" opacity=".2"/><rect x="3" y="7" width="18" height="22" rx="5" fill="currentColor"/><path d="M8.5 14h7.5M8.5 18h7.5M8.5 22h5" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>
                </div>
                <div><strong>Notes</strong><span>Personal workspace</span></div>
            </div>

            <div class="auth-header">
                <div class="auth-kicker">{isForgotMode ? 'ACCOUNT RECOVERY' : isRegisterMode ? 'GET STARTED' : 'WELCOME BACK'}</div>
                <h1>{isForgotMode ? 'Reset your password' : isRegisterMode ? 'Create your account' : 'Sign in to Notes'}</h1>
                <p>
                    {isForgotMode
                        ? 'Enter your email and choose a new password.'
                        : isRegisterMode
                            ? 'Create your secure workspace in a few seconds.'
                            : 'Access your notes and continue where you left off.'}
                </p>
            </div>

            {#if error}
                <div class="message error" role="alert">
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"/><path d="M12 7.5v5M12 16.5h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
                    <span>{error}</span>
                </div>
            {/if}

            {#if success}
                <div class="message success" role="status">
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.7"/><path d="m8 12 2.5 2.5L16 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    <span>{success}</span>
                </div>
            {/if}

            <form onsubmit={handleSubmit}>
                <div class="field">
                    <label for="email">Email address</label>
                    <div class="input-wrap">
                        <svg class="field-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3.5" y="5" width="17" height="14" rx="3" stroke="currentColor" stroke-width="1.7"/><path d="m5.5 7 6.5 5 6.5-5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        <input id="email" type="email" placeholder="you@example.com" bind:value={email} autocomplete="email" required />
                    </div>
                </div>

                {#if isForgotMode}
                    <div class="field">
                        <div class="label-row"><label for="new-password">New password</label><span>{newPassword.length}/6 min</span></div>
                        <div class="input-wrap">
                            <svg class="field-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2.5" stroke="currentColor" stroke-width="1.7"/><path d="M8 10V7.5a4 4 0 0 1 8 0V10" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="15" r="1" fill="currentColor"/></svg>
                            <input id="new-password" type={showNewPassword ? 'text' : 'password'} placeholder="Create a new password" bind:value={newPassword} autocomplete="new-password" minlength="6" required />
                            <button class="visibility" type="button" aria-label={showNewPassword ? 'Hide password' : 'Show password'} onclick={() => showNewPassword = !showNewPassword}>
                                {#if showNewPassword}<svg viewBox="0 0 24 24" fill="none"><path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.8 5.3A10.9 10.9 0 0 1 12 5c5.5 0 9 5 9 7s-3.5 7-9 7a9.8 9.8 0 0 1-5.2-1.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M5.3 8.1C3.8 9.4 3 11 3 12c0 1.3 2.5 5.1 6.8 6.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>{:else}<svg viewBox="0 0 24 24" fill="none"><path d="M3 12s3.5-7 9-7 9 7 9 7-3.5 7-9 7-9-7-9-7Z" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.5" stroke="currentColor" stroke-width="1.7"/></svg>{/if}
                            </button>
                        </div>
                    </div>

                    <div class="strength">
                        <div class="strength-bars">{#each [1,2,3,4] as bar}<span class:filled={passwordStrength(newPassword) >= bar}></span>{/each}</div>
                        <span>{strengthLabels[passwordStrength(newPassword)] || 'Use at least 6 characters'}</span>
                    </div>

                    <div class="field">
                        <label for="confirm-password">Confirm new password</label>
                        <div class="input-wrap">
                            <svg class="field-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2.5" stroke="currentColor" stroke-width="1.7"/><path d="M8 10V7.5a4 4 0 0 1 8 0V10" stroke="currentColor" stroke-width="1.7"/></svg>
                            <input id="confirm-password" type={showConfirmPassword ? 'text' : 'password'} placeholder="Repeat your new password" bind:value={confirmPassword} autocomplete="new-password" minlength="6" required />
                            <button class="visibility" type="button" aria-label={showConfirmPassword ? 'Hide password' : 'Show password'} onclick={() => showConfirmPassword = !showConfirmPassword}>
                                {#if showConfirmPassword}<svg viewBox="0 0 24 24" fill="none"><path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.8 5.3A10.9 10.9 0 0 1 12 5c5.5 0 9 5 9 7s-3.5 7-9 7a9.8 9.8 0 0 1-5.2-1.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>{:else}<svg viewBox="0 0 24 24" fill="none"><path d="M3 12s3.5-7 9-7 9 7 9 7-3.5 7-9 7-9-7-9-7Z" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.5" stroke="currentColor" stroke-width="1.7"/></svg>{/if}
                            </button>
                        </div>
                    </div>
                {:else}
                    <div class="field">
                        <div class="label-row"><label for="password">Password</label>{#if !isRegisterMode}<button type="button" class="forgot-inline" onclick={showForgotPassword}>Forgot password?</button>{/if}</div>
                        <div class="input-wrap">
                            <svg class="field-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2.5" stroke="currentColor" stroke-width="1.7"/><path d="M8 10V7.5a4 4 0 0 1 8 0V10" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="15" r="1" fill="currentColor"/></svg>
                            <input id="password" type={showPassword ? 'text' : 'password'} placeholder={isRegisterMode ? 'Create a password' : 'Enter your password'} bind:value={password} autocomplete={isRegisterMode ? 'new-password' : 'current-password'} required />
                            <button class="visibility" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onclick={() => showPassword = !showPassword}>
                                {#if showPassword}<svg viewBox="0 0 24 24" fill="none"><path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.8 5.3A10.9 10.9 0 0 1 12 5c5.5 0 9 5 9 7s-3.5 7-9 7a9.8 9.8 0 0 1-5.2-1.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M5.3 8.1C3.8 9.4 3 11 3 12c0 1.3 2.5 5.1 6.8 6.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>{:else}<svg viewBox="0 0 24 24" fill="none"><path d="M3 12s3.5-7 9-7 9 7 9 7-3.5 7-9 7-9-7-9-7Z" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.5" stroke="currentColor" stroke-width="1.7"/></svg>{/if}
                            </button>
                        </div>
                    </div>

                    {#if isRegisterMode}
                        <div class="strength">
                            <div class="strength-bars">{#each [1,2,3,4] as bar}<span class:filled={passwordStrength(password) >= bar}></span>{/each}</div>
                            <span>{strengthLabels[passwordStrength(password)] || 'Use at least 6 characters'}</span>
                        </div>
                    {/if}
                {/if}

                <button class="primary-button" type="submit" disabled={loading || googleLoading}>
                    {#if loading}
                        <span class="spinner"></span>
                        {isForgotMode ? 'Resetting password...' : isRegisterMode ? 'Creating account...' : 'Signing in...'}
                    {:else}
                        {isForgotMode ? 'Reset password' : isRegisterMode ? 'Create account' : 'Sign in'}
                        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    {/if}
                </button>
            </form>

            {#if !isRegisterMode && !isForgotMode}
                <div class="divider"><span>OR CONTINUE WITH</span></div>
                <button type="button" class="google-button" onclick={loginWithGoogle} disabled={loading || googleLoading}>
                    {#if googleLoading}
                        <span class="google-spinner"></span> Connecting to Google...
                    {:else}
                        <svg class="google-icon" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M21.35 12.23c0-.79-.07-1.55-.23-2.27H12v4.3h5.23a4.47 4.47 0 0 1-1.94 2.93v2.45h3.14c1.84-1.69 2.92-4.18 2.92-7.41z"/><path fill="#34A853" d="M12 21.75c2.63 0 4.84-.87 6.45-2.36l-3.14-2.45c-.87.58-1.98.92-3.31.92-2.54 0-4.69-1.72-5.46-4.03H3.3v2.53A9.74 9.74 0 0 0 12 21.75z"/><path fill="#FBBC05" d="M6.54 13.83A5.86 5.86 0 0 1 6.23 12c0-.64.11-1.26.31-1.83V7.64H3.3A9.75 9.75 0 0 0 2.25 12c0 1.57.38 3.05 1.05 4.36l3.24-2.53z"/><path fill="#EA4335" d="M12 6.14c1.43 0 2.71.49 3.72 1.45l2.79-2.79C16.84 3.12 14.63 2.25 12 2.25a9.74 9.74 0 0 0-8.7 5.39l3.24 2.53C7.31 7.86 9.46 6.14 12 6.14z"/></svg>
                        Continue with Google
                    {/if}
                </button>
            {/if}

            <div class="switch">
                {#if isForgotMode}
                    <span>Remember your password?</span><button type="button" onclick={backToLogin}>Back to sign in</button>
                {:else if isRegisterMode}
                    <span>Already have an account?</span><button type="button" onclick={switchMode}>Sign in</button>
                {:else}
                    <span>Don't have an account?</span><button type="button" onclick={switchMode}>Create account</button>
                {/if}
            </div>

            <div class="auth-note">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.5 19 6v5.5c0 4.3-2.8 7.6-7 9-4.2-1.4-7-4.7-7-9V6l7-2.5Z" stroke="currentColor" stroke-width="1.6"/><path d="m9 12 2 2 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <span>Your information is protected by your account authentication.</span>
            </div>
        </section>
    </main>
</div>

<style>
    :global(*) { box-sizing: border-box; }

    :global(html), :global(body) {
        margin: 0;
        min-height: 100%;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, Roboto, Helvetica, Arial, sans-serif;
    }

    :global(body) { background: #07090d; color: #f4f5f7; }

    .auth-page {
        position: relative;
        min-height: 100vh;
        min-height: 100svh;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 32px;
        background:
            radial-gradient(circle at 72% 16%, rgba(255, 84, 25, .055), transparent 30%),
            radial-gradient(circle at 18% 85%, rgba(37, 99, 235, .045), transparent 28%),
            #07090d;
    }

    .ambient { position: absolute; border-radius: 999px; pointer-events: none; filter: blur(70px); opacity: .45; }
    .ambient-one { width: 260px; height: 260px; top: -150px; right: 5%; background: rgba(255, 79, 22, .12); }
    .ambient-two { width: 240px; height: 240px; bottom: -150px; left: 4%; background: rgba(34, 90, 170, .08); }

    .auth-shell {
        position: relative;
        z-index: 1;
        width: min(1080px, 100%);
        min-height: 650px;
        display: grid;
        grid-template-columns: 1fr 1.02fr;
        overflow: hidden;
        border: 1px solid #242832;
        border-radius: 24px;
        background: #0d1016;
        box-shadow: 0 35px 100px rgba(0,0,0,.52), 0 0 0 1px rgba(255,255,255,.015) inset;
    }

    .intro-panel {
        position: relative;
        display: flex;
        flex-direction: column;
        padding: 46px 48px;
        border-right: 1px solid #242832;
        background:
            radial-gradient(circle at 10% 15%, rgba(255, 84, 25, .08), transparent 30%),
            linear-gradient(145deg, #11141b 0%, #0b0e13 72%);
    }

    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-icon { width: 42px; height: 42px; display: grid; place-items: center; color: #ff5a1f; border-radius: 12px; background: rgba(255,90,31,.11); border: 1px solid rgba(255,90,31,.17); box-shadow: 0 10px 28px rgba(255,90,31,.08); }
    .brand-icon svg { width: 27px; height: 27px; }
    .brand strong { display: block; color: #f7f7f8; font-size: 18px; line-height: 1.1; letter-spacing: -.02em; }
    .brand span { display: block; margin-top: 3px; color: #747b88; font-size: 12px; }

    .intro-copy { margin-top: auto; margin-bottom: 54px; }
    .eyebrow { display: flex; align-items: center; gap: 8px; color: #ff6a35; font-size: 11px; font-weight: 800; letter-spacing: .12em; }
    .eyebrow span { width: 6px; height: 6px; border-radius: 50%; background: #ff5a1f; box-shadow: 0 0 12px rgba(255,90,31,.7); }
    .intro-copy h2 { margin: 18px 0 14px; color: #f5f6f8; font-family: Georgia, "Times New Roman", serif; font-size: clamp(38px, 4vw, 54px); line-height: .98; letter-spacing: -.045em; font-weight: 600; }
    .intro-copy h2 em { color: #ff6a35; font-style: normal; }
    .intro-copy p { max-width: 420px; margin: 0; color: #8e96a4; font-size: 14px; line-height: 1.75; }

    .feature-list { display: grid; gap: 18px; }
    .feature { display: flex; align-items: center; gap: 13px; }
    .feature-icon { width: 38px; height: 38px; flex: 0 0 38px; display: grid; place-items: center; border-radius: 11px; }
    .feature-icon svg { width: 21px; height: 21px; }
    .feature-icon.orange { color: #ff743f; background: rgba(255,90,31,.09); border: 1px solid rgba(255,90,31,.12); }
    .feature-icon.green { color: #45d88a; background: rgba(34,197,94,.08); border: 1px solid rgba(34,197,94,.11); }
    .feature strong { display: block; color: #dfe2e7; font-size: 13px; font-weight: 650; }
    .feature span { display: block; margin-top: 3px; color: #6f7682; font-size: 11px; }
    .intro-footer { margin-top: auto; padding-top: 30px; display: flex; align-items: center; gap: 8px; color: #69717e; font-size: 11px; }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: #3ddc84; box-shadow: 0 0 12px rgba(61,220,132,.55); }

    .auth-card { padding: 58px 64px 42px; background: #101319; }
    .mobile-brand { display: none; }
    .auth-header { margin-bottom: 28px; }
    .auth-kicker { color: #ff6730; font-size: 10px; font-weight: 800; letter-spacing: .13em; }
    .auth-header h1 { margin: 10px 0 9px; color: #f7f8fa; font-family: Georgia, "Times New Roman", serif; font-size: 38px; line-height: 1.08; letter-spacing: -.035em; font-weight: 600; }
    .auth-header p { margin: 0; color: #858d9b; font-size: 13px; line-height: 1.55; }

    form { display: flex; flex-direction: column; gap: 17px; }
    .field { display: flex; flex-direction: column; gap: 8px; }
    label { color: #dce0e5; font-size: 12px; font-weight: 650; }
    .label-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .label-row > span { color: #59616e; font-size: 10px; }
    .forgot-inline { padding: 0; border: 0; background: none; color: #ff7040; font: inherit; font-size: 11px; font-weight: 600; cursor: pointer; }
    .forgot-inline:hover { color: #ff936d; }

    .input-wrap { position: relative; }
    .field-icon { position: absolute; z-index: 1; left: 14px; top: 50%; width: 18px; height: 18px; color: #68717f; transform: translateY(-50%); pointer-events: none; }
    input { width: 100%; height: 49px; padding: 0 46px 0 42px; border: 1px solid #2a303a; border-radius: 11px; outline: none; background: #0b0e13; color: #f1f3f6; font: inherit; font-size: 13px; transition: border-color .18s ease, box-shadow .18s ease, background .18s ease; }
    input::placeholder { color: #555d69; }
    input:hover { border-color: #343b46; }
    input:focus { border-color: #ff6129; background: #0d1015; box-shadow: 0 0 0 3px rgba(255,90,31,.10); }
    .visibility { position: absolute; right: 8px; top: 50%; width: 34px; height: 34px; display: grid; place-items: center; transform: translateY(-50%); border: 0; border-radius: 8px; background: transparent; color: #68717f; cursor: pointer; }
    .visibility:hover { color: #c8cdd4; background: #171b22; }
    .visibility svg { width: 18px; height: 18px; }

    .strength { display: flex; align-items: center; gap: 10px; margin-top: -7px; }
    .strength-bars { display: flex; gap: 4px; flex: 0 0 96px; }
    .strength-bars span { height: 3px; flex: 1; border-radius: 99px; background: #272d36; transition: background .2s ease; }
    .strength-bars span.filled { background: #ff642d; }
    .strength > span { color: #656e7a; font-size: 10px; }

    .primary-button { width: 100%; height: 50px; display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 4px; border: 1px solid #ff6129; border-radius: 11px; background: linear-gradient(180deg, #ff6229 0%, #f65018 100%); color: #fff; font: inherit; font-size: 13px; font-weight: 750; cursor: pointer; box-shadow: 0 12px 28px rgba(255,79,24,.15); transition: transform .16s ease, box-shadow .16s ease, filter .16s ease; }
    .primary-button svg { width: 17px; height: 17px; transition: transform .16s ease; }
    .primary-button:hover { filter: brightness(1.04); transform: translateY(-1px); box-shadow: 0 15px 34px rgba(255,79,24,.22); }
    .primary-button:hover svg { transform: translateX(2px); }
    .primary-button:active { transform: translateY(0); }
    .primary-button:disabled { opacity: .65; cursor: not-allowed; transform: none; box-shadow: none; }

    .spinner, .google-spinner { width: 16px; height: 16px; border-radius: 50%; border: 2px solid rgba(255,255,255,.35); border-top-color: #fff; animation: spin .7s linear infinite; }
    .google-spinner { border-color: #d8d8d8; border-top-color: #4285f4; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .message { display: flex; align-items: flex-start; gap: 9px; margin-bottom: 17px; padding: 11px 12px; border-radius: 10px; font-size: 11px; line-height: 1.45; }
    .message svg { width: 17px; height: 17px; flex: 0 0 17px; }
    .message.error { color: #ffaaa7; background: rgba(239,68,68,.07); border: 1px solid rgba(239,68,68,.18); }
    .message.success { color: #7ce5aa; background: rgba(34,197,94,.07); border: 1px solid rgba(34,197,94,.18); }

    .divider { display: flex; align-items: center; gap: 12px; margin: 22px 0 14px; color: #565e6b; font-size: 9px; font-weight: 700; letter-spacing: .08em; }
    .divider::before, .divider::after { content: ""; height: 1px; flex: 1; background: #262c35; }

    .google-button { width: 100%; height: 48px; display: flex; align-items: center; justify-content: center; gap: 10px; border: 1px solid #303640; border-radius: 11px; background: #f7f7f8; color: #15171b; font: inherit; font-size: 12px; font-weight: 650; cursor: pointer; transition: transform .16s ease, background .16s ease, box-shadow .16s ease; }
    .google-button:hover { background: #fff; transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,0,0,.2); }
    .google-button:disabled { opacity: .65; cursor: not-allowed; transform: none; }
    .google-icon { width: 19px; height: 19px; }

    .switch { min-height: 42px; display: flex; align-items: center; justify-content: center; gap: 5px; margin-top: 21px; color: #717987; font-size: 11px; text-align: center; }
    .switch button { padding: 0; border: 0; background: none; color: #ff7040; font: inherit; font-size: 11px; font-weight: 700; cursor: pointer; }
    .switch button:hover { color: #ff9a76; text-decoration: underline; text-underline-offset: 3px; }

    .auth-note { display: flex; align-items: center; justify-content: center; gap: 7px; margin-top: 13px; color: #515966; font-size: 9px; text-align: center; line-height: 1.4; }
    .auth-note svg { width: 14px; height: 14px; flex: 0 0 14px; color: #59616d; }

    @media (max-width: 900px) {
        .auth-page { padding: 18px; }
        .auth-shell { grid-template-columns: 1fr; max-width: 560px; min-height: auto; }
        .intro-panel { display: none; }
        .auth-card { padding: 32px 30px 28px; }
        .mobile-brand { display: flex; margin-bottom: 32px; }
    }

    @media (max-width: 520px) {
        .auth-page { padding: 0; align-items: stretch; }
        .auth-shell { min-height: 100svh; border: 0; border-radius: 0; }
        .auth-card { padding: 28px 20px 24px; display: flex; flex-direction: column; justify-content: center; }
        .mobile-brand { margin-bottom: 38px; }
        .auth-header h1 { font-size: 33px; }
        .auth-header { margin-bottom: 25px; }
        .primary-button, .google-button { height: 50px; }
        .auth-note { margin-top: 12px; }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
    }
</style>
