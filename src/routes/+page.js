import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';

export function load() {
    if (browser) {
        const token = sessionStorage.getItem('access_token');

        if (!token) {
            throw redirect(302, '/login');
        }
    }
}