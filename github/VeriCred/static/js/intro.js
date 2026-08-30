/**
 * VeriCred Intro — Video-based
 * --------------------------------
 * Replaces the earlier Three.js 3D scene entirely with a plain video
 * (guards opening the bank doors). Much simpler and far lighter
 * (~2.6MB vs the ~500MB the 3D assets added up to) — no WebGL, no model
 * loading, no GLTFLoader dependency at all.
 */
(function () {
  "use strict";

  const video = document.getElementById("introVideo");
  const skipBtn = document.getElementById("skipIntroBtn");
  const unmuteBtn = document.getElementById("unmuteBtn");
  const vaultOverlay = document.getElementById("vaultOverlay");

  const PORTAL_URL = window.PORTAL_URL || "/portal";

  // Skip immediately if the visitor has already seen the intro this session.
  if (sessionStorage.getItem("vericred_intro_seen") === "1") {
    window.location.href = PORTAL_URL;
    return;
  }

  let transitioning = false;
  function goToPortal() {
    if (transitioning) return;
    transitioning = true;
    sessionStorage.setItem("vericred_intro_seen", "1");
    vaultOverlay.classList.add("visible");
    setTimeout(() => { window.location.href = PORTAL_URL; }, 900);
  }

  skipBtn.addEventListener("click", goToPortal);

  // Video plays once, then transitions automatically.
  video.addEventListener("ended", goToPortal);

  // Safety net: if the video fails to load/play for any reason (unsupported
  // format, blocked autoplay, etc.), don't strand the visitor on a black
  // screen — move on after a few seconds.
  video.addEventListener("error", () => {
    console.error("Intro video failed to load.");
    setTimeout(goToPortal, 1500);
  });

  // Browsers block autoplay-with-sound until the visitor interacts with the
  // page, so the video starts muted. This button lets them turn sound on.
  unmuteBtn.addEventListener("click", () => {
    video.muted = !video.muted;
    unmuteBtn.innerHTML = video.muted ? "&#128264; Unmute" : "&#128266; Mute";
  });
})();
