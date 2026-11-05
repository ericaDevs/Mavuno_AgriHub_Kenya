(() => {
    const initializeScrollReveal = () => {
        if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
            return;
        }

        if (!("IntersectionObserver" in window)) {
            return;
        }

        const targets = document.querySelectorAll(
            "main > *, main section, main article, [data-scroll-reveal]"
        );
        const observer = new IntersectionObserver((entries, currentObserver) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    currentObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.12,
            rootMargin: "0px 0px -24px 0px",
        });

        targets.forEach((target) => {
            target.classList.add("scroll-reveal");
            observer.observe(target);
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeScrollReveal, { once: true });
    } else {
        initializeScrollReveal();
    }
})();
