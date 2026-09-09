/*
 * adminService.js
 *
 * API functions used by the Admin dashboard.
 *
 * Authentication is intentionally NOT handled here.
 * The team leader will connect Supabase authentication later.
 */

import { apiFetch } from './api.js'


// ============================================================
// PROCUREMENT CENTERS
// ============================================================

/**
 * Get all procurement centers.
 */
export async function getAdminCenters() {
    return apiFetch('/centers')
}


/**
 * Update a procurement center.
 *
 * @param {string} centerId
 * @param {Object} updates
 */
export async function updateAdminCenter(centerId, updates) {
    return apiFetch(`/centers/${encodeURIComponent(centerId)}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
    })
}


// ============================================================
// USERS
// ============================================================

/**
 * Get users.
 *
 * @param {string} [role]
 * Optional:
 *   admin
 *   procurement
 *   farmer
 */
export async function getAdminUsers(role) {
    const params = new URLSearchParams()

    if (role) {
        params.set('role', role)
    }

    const query = params.toString()

    return apiFetch(`/users${query ? `?${query}` : ''}`)
}


/**
 * Update a user.
 *
 * @param {string} userId
 * @param {Object} updates
 */
export async function updateAdminUser(userId, updates) {
    return apiFetch(`/users/${encodeURIComponent(userId)}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
    })
}


// ============================================================
// DELETE OPERATIONS
// ============================================================
// These endpoints are being added by the backend teammate.
// We will wire them here once the backend contract is confirmed.
//
// export async function deleteAdminCenter(centerId) {
//     return apiFetch(`/centers/${encodeURIComponent(centerId)}`, {
//         method: 'DELETE',
//     })
// }
//
// export async function deleteAdminUser(userId) {
//     return apiFetch(`/users/${encodeURIComponent(userId)}`, {
//         method: 'DELETE',
//     })
// }