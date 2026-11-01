(() => {
    const form = document.getElementById("mpesa-form");
    if (!form) return;

    const button = document.getElementById("mpesa-submit");
    const message = document.getElementById("mpesa-message");
    const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]").value;

    const showMessage = (text) => {
        message.textContent = text;
    };

    const fetchJson = async (url, options) => {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || data.message || "Payment request failed");
        }
        return data;
    };

    const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

    const pollPayment = async (statusUrl, successUrl) => {
        for (let attempt = 0; attempt < 60; attempt += 1) {
            await wait(3000);
            const status = await fetchJson(statusUrl);
            if (status.status === "SUCCESS") {
                window.location.assign(successUrl);
                return;
            }
            if (status.status !== "PENDING") {
                throw new Error(status.message || "Payment was not completed");
            }
            if (status.message) showMessage(status.message);
        }
        throw new Error("Payment is still pending. Refresh this page to check again.");
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        button.disabled = true;
        showMessage("Sending M-Pesa prompt...");

        try {
            const data = await fetchJson(form.dataset.paymentUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ phone: form.elements.phone.value }),
            });
            showMessage(data.message || "Check your phone and enter your M-Pesa PIN.");
            await pollPayment(data.status_url, data.success_url);
        } catch (error) {
            showMessage(error.message || "Could not complete the payment request.");
            button.disabled = false;
        }
    });
})();