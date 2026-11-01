(() => {
    const form = document.getElementById("mpesa-form");
    if (!form) return;

    const button = document.getElementById("mpesa-submit");
    const container = document.getElementById("mpesa-confirmation-box");
    const message = document.getElementById("mpesa-message");
    const icon = document.getElementById("mpesa-status-icon");
    const csrfInput = form.querySelector("[name=csrfmiddlewaretoken]");
    const csrfToken = csrfInput ? csrfInput.value : "";
    const originalButtonText = button ? button.textContent : "Pay with M-Pesa";

    const setConfirmationStatus = (type, text) => {
        if (!message) return;

        if (container) {
            container.classList.remove(
                "hidden",
                "bg-blue-50", "text-blue-900", "border-blue-200",
                "bg-green-50", "text-green-900", "border-green-200",
                "bg-amber-50", "text-amber-900", "border-amber-200",
                "bg-stone-50", "text-stone-900", "border-stone-300"
            );
            container.classList.add("border");

            if (type === "success") {
                container.classList.add("bg-green-50", "text-green-900", "border-green-200");
                if (icon) icon.textContent = "✓";
            } else if (type === "cancelled") {
                container.classList.add("bg-amber-50", "text-amber-900", "border-amber-200");
                if (icon) icon.textContent = "ℹ";
            } else if (type === "failed") {
                container.classList.add("bg-stone-50", "text-stone-900", "border-stone-300");
                if (icon) icon.textContent = "ℹ";
            } else {
                // info / pending
                container.classList.add("bg-blue-50", "text-blue-900", "border-blue-200");
                if (icon) icon.textContent = "⏳";
            }
        }
        message.textContent = text;
    };

    const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

    const pollPayment = async (statusUrl) => {
        for (let attempt = 0; attempt < 60; attempt += 1) {
            await wait(3000);
            try {
                const response = await fetch(statusUrl, {
                    headers: { "Accept": "application/json" },
                });
                const status = await response.json();

                if (status.status === "SUCCESS") {
                    setConfirmationStatus("success", status.message || "Payment confirmed successfully! Loading your order confirmation...");
                    if (button) {
                        button.disabled = true;
                        button.textContent = "Payment Confirmed";
                    }
                    await wait(1200);
                    if (status.success_url) {
                        window.location.assign(status.success_url);
                    }
                    return;
                }

                if (status.status === "CANCELLED") {
                    setConfirmationStatus("cancelled", status.message || "Payment was cancelled. You can retry with M-Pesa whenever you are ready.");
                    if (button) {
                        button.disabled = false;
                        button.textContent = "Retry Payment";
                    }
                    return;
                }

                if (status.status === "FAILED" || status.status === "TIMEOUT") {
                    setConfirmationStatus("failed", status.message || "Payment could not be completed. You can try again.");
                    if (button) {
                        button.disabled = false;
                        button.textContent = "Try Again";
                    }
                    return;
                }

                // Still PENDING
                if (status.message) {
                    setConfirmationStatus("info", status.message);
                }
            } catch (e) {
                // Network glitch while polling; continue checking smoothly
            }
        }

        setConfirmationStatus("failed", "Payment request timed out. Please try again.");
        if (button) {
            button.disabled = false;
            button.textContent = "Try Again";
        }
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (button) {
            button.disabled = true;
            button.textContent = "Processing...";
        }
        setConfirmationStatus("info", "Sending M-Pesa prompt to your phone...");

        try {
            const phoneValue = form.elements.phone ? form.elements.phone.value : "";
            const response = await fetch(form.dataset.paymentUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ phone: phoneValue }),
            });

            const data = await response.json();

            if (!data.ok) {
                setConfirmationStatus("failed", data.message || "Payment prompt could not be sent. Please check the phone number and try again.");
                if (button) {
                    button.disabled = false;
                    button.textContent = "Try Again";
                }
                return;
            }

            setConfirmationStatus("info", data.message || "Prompt sent to your phone! Please enter your M-Pesa PIN.");
            await pollPayment(data.status_url);
        } catch (error) {
            setConfirmationStatus("failed", "Unable to reach the payment service. Please try again.");
            if (button) {
                button.disabled = false;
                button.textContent = "Try Again";
            }
        }
    });
})();
