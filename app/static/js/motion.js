/*
 * CIVICTRACK — SPARK ENGINE
 *
 * Lightweight canvas particles.
 * Features:
 * - Floating cyan and blue sparks
 * - Pointer-reactive ambient glow
 * - Visibility-aware animation
 * - Reduced-motion support
 * - Scroll reveal animations
 */

(() => {

    "use strict";


    // ==========================================
    // CONFIGURATION
    // ==========================================

    const hero = document.querySelector(".hero");

    if (!hero) {
        return;
    }

    const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;


    // ==========================================
    // CREATE SPARK CANVAS
    // ==========================================

    const canvas = document.createElement("canvas");

    canvas.id = "civictrack-sparks";
    canvas.setAttribute("aria-hidden", "true");

    hero.prepend(canvas);

    const ctx = canvas.getContext("2d", {
        alpha: true
    });

    if (!ctx) {
        canvas.remove();
        return;
    }


    // ==========================================
    // ENGINE STATE
    // ==========================================

    let width = 1;
    let height = 1;

    let pixelRatio = 1;

    let sparks = [];

    let animationFrame = 0;

    let heroVisible = true;
    let pageVisible = !document.hidden;

    const pointer = {
        x: 0,
        y: 0,
        active: false,
        strength: 0
    };


    // ==========================================
    // SPARK GENERATOR
    // ==========================================

    function random(min, max) {
        return Math.random() * (max - min) + min;
    }

    function createSpark() {

        return {
            x: random(0, width),
            y: random(0, height),

            vx: random(-0.12, 0.12),
            vy: random(-0.30, -0.10),

            size: random(0.6, 1.7),

            trail: random(10, 25),

            phase: random(0, Math.PI * 2),

            frequency: random(1.2, 3.2),

            opacity: random(0.35, 0.85),

            color: Math.random() > 0.5
                ? "0,217,255"
                : "23,107,255"
        };
    }


    // ==========================================
    // CANVAS RESIZING
    // ==========================================

    function resizeCanvas() {

        const rect = hero.getBoundingClientRect();

        width = Math.max(1, rect.width);
        height = Math.max(1, rect.height);

        pixelRatio = Math.min(
            window.devicePixelRatio || 1,
            1.5
        );

        canvas.width = Math.round(width * pixelRatio);
        canvas.height = Math.round(height * pixelRatio);

        ctx.setTransform(
            pixelRatio,
            0,
            0,
            pixelRatio,
            0,
            0
        );

        const count = Math.min(
            34,
            Math.max(18, Math.round(width / 38))
        );

        sparks = Array.from(
            { length: count },
            createSpark
        );

        paint(0);

        startAnimation();
    }


    // ==========================================
    // POINTER GLOW
    // ==========================================

    if (!reduceMotion) {

        hero.addEventListener(
            "pointermove",
            event => {

                if (event.pointerType === "touch") {
                    return;
                }

                const rect = hero.getBoundingClientRect();

                pointer.x = event.clientX - rect.left;
                pointer.y = event.clientY - rect.top;

                pointer.active = true;

            },
            { passive: true }
        );


        hero.addEventListener(
            "pointerleave",
            () => {
                pointer.active = false;
            },
            { passive: true }
        );

    }


    // ==========================================
    // DRAW THE PARTICLES
    // ==========================================

    function paint(timestamp) {

        ctx.clearRect(
            0,
            0,
            width,
            height
        );

        const seconds = timestamp / 1000;


        // --------------------------------------
        // POINTER-REACTIVE LIGHT
        // --------------------------------------

        if (!reduceMotion) {

            const target = pointer.active ? 1 : 0;

            pointer.strength +=
                (target - pointer.strength) * 0.07;

        }

        if (pointer.strength > 0.01) {

            const glow = ctx.createRadialGradient(
                pointer.x,
                pointer.y,
                0,
                pointer.x,
                pointer.y,
                150
            );

            glow.addColorStop(
                0,
                `rgba(0,217,255,${pointer.strength * 0.12})`
            );

            glow.addColorStop(
                0.5,
                `rgba(23,107,255,${pointer.strength * 0.06})`
            );

            glow.addColorStop(
                1,
                "rgba(23,107,255,0)"
            );

            ctx.fillStyle = glow;

            ctx.fillRect(
                pointer.x - 150,
                pointer.y - 150,
                300,
                300
            );

        }


        // --------------------------------------
        // DRAW EVERY SPARK
        // --------------------------------------

        for (const spark of sparks) {

            if (!reduceMotion) {

                spark.x += spark.vx;
                spark.y += spark.vy;

                if (
                    spark.y < -20 ||
                    spark.x < -25 ||
                    spark.x > width + 25
                ) {

                    spark.x = random(0, width);
                    spark.y = height + random(2, 30);

                }

            }

            const pulse = reduceMotion
                ? 0.8
                : 0.65 + Math.sin(
                    seconds * spark.frequency + spark.phase
                ) * 0.25;

            const alpha = spark.opacity * pulse;


            // Spark trail

            if (!reduceMotion) {

                ctx.beginPath();

                ctx.moveTo(
                    spark.x,
                    spark.y
                );

                ctx.lineTo(
                    spark.x - spark.vx * spark.trail,
                    spark.y - spark.vy * spark.trail
                );

                ctx.strokeStyle =
                    `rgba(${spark.color},${alpha * 0.65})`;

                ctx.lineWidth = spark.size;

                ctx.stroke();

            }


            // Bright spark core

            ctx.beginPath();

            ctx.arc(
                spark.x,
                spark.y,
                spark.size,
                0,
                Math.PI * 2
            );

            ctx.fillStyle =
                `rgba(225,250,255,${alpha})`;

            ctx.fill();

        }

    }


    // ==========================================
    // ANIMATION LOOP
    // ==========================================

    function frame(timestamp) {

        animationFrame = 0;

        paint(timestamp);

        if (
            !reduceMotion &&
            pageVisible &&
            heroVisible
        ) {

            animationFrame =
                requestAnimationFrame(frame);

        }

    }


    function startAnimation() {

        if (
            reduceMotion ||
            !pageVisible ||
            !heroVisible ||
            animationFrame
        ) {
            return;
        }

        animationFrame =
            requestAnimationFrame(frame);

    }


    function stopAnimation() {

        if (animationFrame) {

            cancelAnimationFrame(animationFrame);

            animationFrame = 0;

        }

    }


    // ==========================================
    // PAUSE WHEN THE HERO IS OFF-SCREEN
    // ==========================================

    if ("IntersectionObserver" in window) {

        const heroObserver = new IntersectionObserver(
            entries => {

                for (const entry of entries) {

                    heroVisible = entry.isIntersecting;

                    if (heroVisible) {
                        startAnimation();
                    } else {
                        stopAnimation();
                    }

                }

            },
            {
                threshold: 0.01
            }
        );

        heroObserver.observe(hero);

    }


    // ==========================================
    // PAUSE WHEN THE TAB IS HIDDEN
    // ==========================================

    document.addEventListener(
        "visibilitychange",
        () => {

            pageVisible = !document.hidden;

            if (pageVisible) {
                startAnimation();
            } else {
                stopAnimation();
            }

        }
    );


    // ==========================================
    // RESPONSIVE CANVAS
    // ==========================================

    if ("ResizeObserver" in window) {

        const resizeObserver = new ResizeObserver(
            resizeCanvas
        );

        resizeObserver.observe(hero);

    } else {

        window.addEventListener(
            "resize",
            resizeCanvas,
            { passive: true }
        );

    }


    // ==========================================
    // SCROLL REVEAL SYSTEM
    // ==========================================

    if (
        !reduceMotion &&
        "IntersectionObserver" in window
    ) {

        const revealTargets = document.querySelectorAll(
            [
                ".section-heading",
                ".stat-card",
                ".report-panel",
                ".process-panel",
                ".complaints-panel",
                ".process-step"
            ].join(",")
        );

        revealTargets.forEach(element => {

            element.classList.add("ct-reveal");

            if (element.classList.contains("stat-card")) {

                const siblings = [
                    ...element.parentElement.children
                ];

                const index = siblings.indexOf(element);

                element.style.setProperty(
                    "--ct-reveal-delay",
                    `${index * 100}ms`
                );

            }

        });


        const revealObserver = new IntersectionObserver(
            (entries, observer) => {

                entries.forEach(entry => {

                    if (entry.isIntersecting) {

                        entry.target.classList.add(
                            "ct-visible"
                        );

                        observer.unobserve(entry.target);

                    }

                });

            },
            {
                threshold: 0.12,
                rootMargin: "0px 0px -25px 0px"
            }
        );


        revealTargets.forEach(element => {
            revealObserver.observe(element);
        });

    }


    // ==========================================
    // INITIALIZE
    // ==========================================

    resizeCanvas();

})();
