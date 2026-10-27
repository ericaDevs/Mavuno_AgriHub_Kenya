(() => {
    const updateCartBadge = (count) => {
        document.querySelectorAll("[data-cart-link]").forEach((cartLink) => {
            cartLink.dataset.count = String(count);
            cartLink.setAttribute(
                "aria-label",
                `Shopping cart, ${count} ${count === 1 ? "item" : "items"}`
            );

            let badge = cartLink.querySelector("[data-cart-badge]");
            if (count === 0) {
                badge?.remove();
                return;
            }

            if (!badge) {
                badge = document.createElement("span");
                badge.dataset.cartBadge = "";
                badge.setAttribute("role", "status");
                badge.setAttribute("aria-live", "polite");
                badge.className = "absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full border-2 border-white bg-red-600 px-1 text-[10px] font-extrabold leading-none text-white";
                cartLink.appendChild(badge);
            }
            badge.textContent = String(count);
        });
    };

    const updateCartPageCount = (count) => {
        const countLabel = document.querySelector("[data-cart-page-count]");
        if (countLabel) {
            countLabel.textContent = count
                ? `${count} item${count === 1 ? "" : "s"} ready for your farm`
                : "Review your selected farm products";
        }
    };

    const showCartMessage = (message, isError) => {
        let feedback = document.getElementById("cart-feedback");
        if (!feedback) {
            feedback = document.createElement("div");
            feedback.id = "cart-feedback";
            feedback.className = "fixed right-4 top-24 z-[100] max-w-sm space-y-2";
            feedback.setAttribute("aria-live", "polite");
            document.body.appendChild(feedback);
        }

        const notice = document.createElement("p");
        notice.className = `rounded-xl border bg-white px-4 py-3 text-sm font-semibold shadow-lg ${
            isError ? "border-red-200 text-red-800" : "border-agri-leaf/20 text-agri-forest"
        }`;
        notice.textContent = message;
        feedback.appendChild(notice);
        window.setTimeout(() => notice.remove(), 4000);
    };

    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("form[data-cart-operation]");
        if (!form) {
            return;
        }

        event.preventDefault();
        const submitButton = event.submitter || form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
        }

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                credentials: "same-origin",
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });

            const contentType = response.headers.get("content-type") || "";
            let data = null;
            if (contentType.includes("application/json")) {
                data = await response.json();
            }

            if (!response.ok) {
                const message = (data && data.error)
                    ? data.error
                    : (response.status === 403
                        ? "Permission denied (CSRF origin check failed). Please refresh and try again."
                        : `Request failed with status ${response.status}. Please try again.`);
                throw new Error(message);
            }

            if (!data) {
                throw new Error("Invalid response received from the server.");
            }

            updateCartBadge(data.item_count);
            updateCartPageCount(data.item_count);

            const cartContent = document.getElementById("cart-content");
            if (cartContent && typeof data.cart_html === "string") {
                cartContent.innerHTML = data.cart_html;
                if (window.lucide && typeof window.lucide.createIcons === "function") {
                    window.lucide.createIcons();
                }
            }

            (data.messages || []).forEach(({ text, tags }) => {
                showCartMessage(text, (tags || "").includes("error"));
            });
        } catch (error) {
            showCartMessage(error.message || "The cart could not be updated. Please try again.", true);
        } finally {
            if (submitButton && submitButton.isConnected) {
                submitButton.disabled = false;
            }
        }
    });
})();
