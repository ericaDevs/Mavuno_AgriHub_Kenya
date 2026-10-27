async function payWithMpesa(orderId, phone) {
    const r = await fetch(`/payments/mpesa/pay/${orderId}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify({ phone }),
    });
    const data = await r.json();
    if (!data.ok) return showError(data.error);
    showMessage("Check your phone and enter your M-Pesa PIN...");

    const timer = setInterval(async () => {
        const s = await (await fetch(`/payments/mpesa/status/${data.payment_id}/`)).json();
        if (s.status !== "PENDING") {
            clearInterval(timer);
            s.status === "SUCCESS" ? window.location = `/orders/${orderId}/thanks/`
                : showError(s.message || "Payment not completed");
        }
    }, 3000);
}