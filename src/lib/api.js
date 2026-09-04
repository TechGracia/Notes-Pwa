const API_URL = "http://localhost:8000";

// =========================================================
// LOGIN
// =========================================================

export async function loginUser(email, password) {
    const formData = new URLSearchParams();

    formData.append("username", email);
    formData.append("password", password);

    const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: formData
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Login failed"
        );
    }

    // Store authentication per browser tab.
    sessionStorage.setItem(
        "access_token",
        data.access_token
    );

    return data;
}


// =========================================================
// CREATE USER
// =========================================================

export async function createUser(email, password) {
    const response = await fetch(`${API_URL}/users`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email,
            password
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to create user"
        );
    }

    return data;
}


// =========================================================
// GET TOKEN
// =========================================================

export function getToken() {
    return sessionStorage.getItem("access_token");
}


// =========================================================
// AUTHORIZATION HEADER
// =========================================================

function authHeaders() {
    const token = getToken();

    return {
        "Content-Type": "application/json",

        ...(token
            ? {
                  "Authorization": `Bearer ${token}`
              }
            : {})
    };
}


// =========================================================
// CREATE NOTE
// =========================================================

export async function createNote(title, content) {
    const response = await fetch(`${API_URL}/notes`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
            title,
            content
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to create note"
        );
    }

    return data;
}


// =========================================================
// GET NOTES
// =========================================================

export async function getNotes() {
    const response = await fetch(`${API_URL}/notes`, {
        method: "GET",
        headers: authHeaders()
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to fetch notes"
        );
    }

    return data;
}


// =========================================================
// GET SINGLE NOTE
// =========================================================

export async function getNote(noteId) {
    const response = await fetch(
        `${API_URL}/notes/${noteId}`,
        {
            method: "GET",
            headers: authHeaders()
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to fetch note"
        );
    }

    return data;
}


// =========================================================
// UPDATE NOTE
// =========================================================

export async function updateNote(
    noteId,
    title,
    content
) {
    const response = await fetch(
        `${API_URL}/notes/${noteId}`,
        {
            method: "PUT",
            headers: authHeaders(),
            body: JSON.stringify({
                title,
                content
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to update note"
        );
    }

    return data;
}


// =========================================================
// DELETE NOTE
// =========================================================

export async function deleteNote(noteId) {
    const response = await fetch(
        `${API_URL}/notes/${noteId}`,
        {
            method: "DELETE",
            headers: authHeaders()
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to delete note"
        );
    }

    return data;
}


// =========================================================
// CHANGE PASSWORD
// =========================================================

export async function changePassword(
    currentPassword,
    newPassword
) {
    const response = await fetch(
        `${API_URL}/change-password`,
        {
            method: "PUT",
            headers: authHeaders(),
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to change password"
        );
    }

    return data;
}


// =========================================================
// LOGOUT
// =========================================================

export function logout() {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user_id");
    sessionStorage.removeItem("user_email");
}


// =========================================================
// FORGOT PASSWORD
// =========================================================

export async function forgotPassword(
    email,
    newPassword
) {
    const response = await fetch(
        `${API_URL}/forgot-password`,
        {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email,
                new_password: newPassword
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Failed to reset password"
        );
    }

    return data;
}


// =========================================================
// GET CURRENT USER
// =========================================================

export async function getCurrentUser() {
    const token = getToken();

    if (!token) {
        throw new Error("No authentication token found");
    }

    const response = await fetch(
        `${API_URL}/me`,
        {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            }
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Could not validate login"
        );
    }

    // Keep useful user information in the current tab.
    if (data.id !== undefined) {
        sessionStorage.setItem(
            "user_id",
            String(data.id)
        );
    }

    if (data.email) {
        sessionStorage.setItem(
            "user_email",
            data.email
        );
    }

    return data;
}