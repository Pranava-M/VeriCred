/**
 * Site-wide page effects for the portal (non-intro pages).
 * - Lenis: smooth scrolling
 * - GSAP: fade-in on load, fade-out transition before navigating to
 *   another internal page (approximates SPA-smooth transitions without
 *   rewriting the Flask/Jinja app as a React SPA)
 * - Nav "More" dropdown toggle
 */
(function () {
  "use strict";

  // Smooth scroll
  if (window.Lenis) {
    const lenis = new Lenis({ duration: 1.0, smoothWheel: true });
    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);
  }

  // Fade the page in on load
  if (window.gsap) {
    gsap.set("body", { opacity: 0 });
    gsap.to("body", { opacity: 1, duration: 0.45, ease: "power1.out" });
  }

  // Fade-out transition before internal navigation
  const overlay = document.getElementById("pageTransitionOverlay");
  const rupee = document.getElementById("pageTransitionRupee");
  if (overlay && window.gsap) {
    document.querySelectorAll('a[href^="/"]').forEach((link) => {
      link.addEventListener("click", function (e) {
        const href = this.getAttribute("href");
        if (!href || href.startsWith("#") || this.target === "_blank") return;
        e.preventDefault();
        if (rupee) {
          rupee.classList.remove("spin");
          void rupee.offsetWidth; // force reflow so the animation restarts cleanly
          rupee.classList.add("spin");
        }
        gsap.to(overlay, {
          opacity: 1,
          duration: 0.28,
          ease: "power1.in",
          onComplete: () => { window.location.href = href; },
        });
      });
    });
  }

  // Nav "More" dropdown
  const moreToggle = document.getElementById("navMoreToggle");
  const moreWrap = document.getElementById("navMoreWrap");
  if (moreToggle && moreWrap) {
    moreToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      moreWrap.classList.toggle("open");
    });
    document.addEventListener("click", () => moreWrap.classList.remove("open"));
  }
})();
