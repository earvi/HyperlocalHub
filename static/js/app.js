document.addEventListener("DOMContentLoaded", () => {

    /* ===============================
       Sidebar Active Link Highlight
    ================================ */
    const currentPath = window.location.pathname.replace(/\/$/, "");
    const links = document.querySelectorAll(".sidebar-link");

    links.forEach(link => {
        const href = link.getAttribute("href");
        if (!href) return;

        const cleanHref = href.replace(/\/$/, "");

        if (
            cleanHref === currentPath ||
            (currentPath.startsWith("/admin") && cleanHref.startsWith("/admin"))
        ) {
            link.classList.add("active");
        }
    });

    /* ===============================
       Bookmark Toggle
    ================================ */
    document.querySelectorAll(".bookmark-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();

            const alertId = btn.dataset.alertId;
            if (!alertId) return;

            const icon = btn.querySelector("i");
            if (!icon) return;

            const isBookmarked = icon.classList.contains("bi-star-fill");

            const url = isBookmarked
                ? `/bookmark/${alertId}/remove`
                : `/bookmark/${alertId}`;

            try {
                const res = await fetch(url, {
                    method: "POST",
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                });

                if (res.status === 401) {
                    alert("Please log in to use bookmarks.");
                    return;
                }

                if (!res.ok) {
                    console.error("Request failed:", res.status);
                    return;
                }

                const data = await res.json();
                if (!data.ok) {
                    console.error("Server error:", data);
                    return;
                }

                // Toggle icon
                icon.classList.toggle("bi-star-fill", !isBookmarked);
                icon.classList.toggle("bi-star", isBookmarked);
                icon.classList.toggle("text-warning", !isBookmarked);
                icon.classList.toggle("text-secondary", isBookmarked);

            } catch (err) {
                console.error("Bookmark error:", err);
            }
        });
    });

    /* ===============================
       Theme Toggle (Dark / Light)
    ================================ */
    const toggle = document.getElementById("theme-toggle");
    const root = document.documentElement;

    if (toggle) {
        const savedTheme = localStorage.getItem("hl_theme") || "dark";
        root.setAttribute("data-theme", savedTheme);
        toggle.checked = savedTheme === "dark";

        toggle.addEventListener("change", () => {
            const theme = toggle.checked ? "dark" : "light";
            root.setAttribute("data-theme", theme);
            localStorage.setItem("hl_theme", theme);
        });
    }
    /* ===============================
       Mobile Sidebar Toggle
    ================================ */
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const sidebar = document.getElementById("sidebar");

    function toggleSidebar() {
        sidebar.classList.toggle("active");
        sidebarOverlay.classList.toggle("active");
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", toggleSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener("click", toggleSidebar);
    }



    /* ===============================
       Socket.IO Real-time Chat
    ================================ */
    const socket = io();

    socket.on('connect', () => {
        console.log("Socket Connected!", socket.id);
    });

    socket.on('new_comment', (data) => {
        console.log("New Comment Received:", data);
        const listDiv = document.getElementById(`comments-list-${data.alert_id}`);

        // Only append if the section is visible (i.e., user is watching this alert)
        if (listDiv && !listDiv.closest('.d-none')) {
            // Remove "No comments" message if it exists
            if (listDiv.innerHTML.includes("No comments yet")) {
                listDiv.innerHTML = "";
            }

            const newCommentHTML = `
                <div class="comment mb-2 p-2 rounded position-relative slide-in" style="background: rgba(255,255,255,0.1); border-left: 3px solid var(--neon-lime);">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong class="small text-primary">${data.user}</strong>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge bg-danger" style="font-size: 0.6rem;">NEW</span>
                            <small class="text-muted" style="font-size: 0.7rem;">Just now</small>
                        </div>
                    </div>
                    <div class="small mt-1">${data.text}</div>
                </div>
            `;
            listDiv.insertAdjacentHTML('beforeend', newCommentHTML);
        }
    });

    /* ===============================
       Comment Toggle & Fetch
    ================================ */
    document.querySelectorAll(".comment-toggle-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const alertId = btn.dataset.alertId;
            const section = document.getElementById(`comments-${alertId}`);

            section.classList.toggle("d-none");

            if (!section.classList.contains("d-none")) {
                // Fetch comments if opening
                loadComments(alertId);

                // Join Socket Room
                socket.emit('join_alert', { alert_id: alertId });
            } else {
                // Leave Room (Optional, but good practice)
                socket.emit('leave_alert', { alert_id: alertId });
            }
        });
    });

    async function loadComments(alertId) {
        const listDiv = document.getElementById(`comments-list-${alertId}`);
        listDiv.innerHTML = '<div class="text-center text-muted small">Loading...</div>';

        try {
            const res = await fetch(`/alert/${alertId}/comments`);
            const data = await res.json();

            if (data.ok) {
                if (data.comments.length === 0) {
                    listDiv.innerHTML = '<div class="text-center text-muted small">No comments yet. Be the first!</div>';
                } else {
                    listDiv.innerHTML = data.comments.map(c => `
                        <div class="comment mb-2 p-2 rounded position-relative" style="background: rgba(255,255,255,0.05);">
                            <div class="d-flex justify-content-between align-items-center">
                                <strong class="small text-primary">${c.user}</strong>
                                <div class="d-flex align-items-center gap-2">
                                    <small class="text-muted" style="font-size: 0.7rem;">${c.created_at}</small>
                                    ${c.is_owner ? `
                                    <button class="btn btn-link p-0 text-danger delete-comment-btn" data-comment-id="${c.id}" data-alert-id="${alertId}" style="line-height:1;">
                                        <i class="bi bi-trash small"></i>
                                    </button>` : ''}
                                </div>
                            </div>
                            <div class="small mt-1">${c.text}</div>
                        </div>
                    `).join("");

                    // Attach Delete Handlers
                    listDiv.querySelectorAll(".delete-comment-btn").forEach(btn => {
                        btn.addEventListener("click", async () => {
                            if (!confirm("Delete this comment?")) return;
                            const commentId = btn.dataset.commentId;
                            try {
                                const delRes = await fetch(`/comment/${commentId}/delete`, { method: "POST" });
                                const delData = await delRes.json();
                                if (delData.ok) {
                                    loadComments(alertId); // Reload
                                } else {
                                    alert(delData.error || "Failed to delete");
                                }
                            } catch (e) {
                                console.error(e);
                            }
                        });
                    });
                }
            }
        } catch (err) {
            listDiv.innerHTML = '<div class="text-danger small">Failed to load comments.</div>';
        }
    }

    /* ===============================
       Comment Submission
    ================================ */
    document.querySelectorAll(".comment-form").forEach(form => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const alertId = form.dataset.alertId;
            const input = form.querySelector("input");
            const text = input.value.trim();

            if (!text) return;

            try {
                const res = await fetch(`/alert/${alertId}/comment`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ text })
                });
                const data = await res.json();

                if (data.ok) {
                    input.value = ""; // Clear input
                    loadComments(alertId); // Reload list

                    // Ideally update count too, but that requires selecting the button
                } else if (data.error === "login_required") {
                    window.location.href = "/auth/login";
                }
            } catch (err) {
                console.error("Comment failed:", err);
            }
        });
    });

}); // End of original DOMContentLoaded



/* ===============================
   Push Notifications Logic
================================ */
const publicVapidKey = "BAbJzSof41K61uT9X2QZNkZuTm2U-qc6TA-oriEtcVdur0Z3IwzibWjTMDrpXIC30SB0GBSUeFnoZygWIgpie-s";

document.addEventListener("DOMContentLoaded", () => {
    const pushToggle = document.getElementById("pushToggle");
    if (pushToggle) {
        checkPushState(pushToggle);

        pushToggle.addEventListener("change", async () => {
            if (pushToggle.checked) {
                await subscribeUser();
            } else {
                await unsubscribeUser();
            }
            updatePushUI(pushToggle.checked);
        });
    }
});

function updatePushUI(isEnabled) {
    const statusText = document.getElementById("pushStatusText");
    const icon = document.querySelector(".bi-broadcast");

    if (statusText) {
        if (isEnabled) {
            statusText.textContent = "Active - Receiving Alerts";
            statusText.className = "small text-info";
            if (icon) icon.className = "bi bi-broadcast me-2 fs-5 text-info inner-glow";
        } else {
            statusText.textContent = "Disabled";
            statusText.className = "small text-muted";
            if (icon) icon.className = "bi bi-broadcast me-2 fs-5 text-muted";
        }
    }
}

async function checkPushState(toggle) {
    if (!('serviceWorker' in navigator)) {
        toggle.disabled = true;
        const statusText = document.getElementById("pushStatusText");
        if (statusText) statusText.textContent = "Not Supported";
        return;
    }

    // Register SW if not already (just in case)
    await registerServiceWorker();

    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();

    // Auto-resubscribe if key changed or broken? No, just check state.
    const isSubscribed = !!sub;

    toggle.checked = isSubscribed;
    updatePushUI(isSubscribed);
    console.log("Push State Checked:", isSubscribed);
}

async function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
        try {
            const register = await navigator.serviceWorker.register("/static/sw.js", {
                scope: "/static/"
            });
            console.log("Service Worker Registered...");
            return register;
        } catch (err) {
            console.error("SW Register Failed:", err);
        }
    }
}

async function subscribeUser() {
    // 1. Ask for Permission Explicitly
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        alert("Permission denied or dismissed. Please enable notifications in your browser settings.");
        document.getElementById("pushToggle").checked = false;
        updatePushUI(false);
        return;
    }

    const register = await registerServiceWorker();
    if (!register) return;

    // Wait for SW to be ready
    await navigator.serviceWorker.ready;

    console.log("Registering Push...");
    try {
        const subscription = await register.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
        });
        console.log("Push Registered...");

        // Send to API
        await fetch("/api/v1/subscribe", {
            method: "POST",
            body: JSON.stringify(subscription),
            headers: {
                "content-type": "application/json"
            }
        });
        console.log("Push Sent to Server...");
    } catch (e) {
        console.error("Failed to subscribe:", e);
        document.getElementById("pushToggle").checked = false;
        updatePushUI(false);
        alert("Failed to enable notifications. See console for details.");
    }
}

async function unsubscribeUser() {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
        await sub.unsubscribe();
        console.log("User Unsubscribed.");
    }
}

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, "+")
        .replace(/_/g, "/");

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

/* ===============================
   Geolocation Logic
================================ */
function getNearMe(e) {
    if (e) e.preventDefault();

    if (!navigator.geolocation) {
        window.location.href = "/map";
        return;
    }

    // Show loading state
    const link = e.target.closest('a');
    const icon = link ? link.querySelector('i') : null;
    if (icon) {
        icon.className = "bi bi-hourglass-split";
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            // Redirect to Map with params
            window.location.href = `/map?lat=${lat}&lon=${lon}`;
        },
        (error) => {
            console.warn("Geo Error:", error);
            // Fallback to generic map if denied or error
            window.location.href = "/map";
        },
        { timeout: 5000 }
    );
}
