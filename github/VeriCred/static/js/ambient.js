/**
 * Ambient nav background — a quiet, drifting network of nodes/lines,
 * evoking "data verifying in the background" without being distracting.
 * Deliberately scoped to the dark top nav bar only (not the full light
 * content area) so readability of dashboard content is never affected.
 */
(function () {
  "use strict";
  const wrap = document.getElementById("ambientCanvasWrap");
  if (!wrap) return;

  const canvas = document.createElement("canvas");
  wrap.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  let width, height, nodes;
  const NODE_COUNT = 26;
  const LINK_DIST = 90;

  function resize() {
    width = wrap.clientWidth;
    height = wrap.clientHeight;
    canvas.width = width * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
  }

  function initNodes() {
    nodes = Array.from({ length: NODE_COUNT }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.25,
      vy: (Math.random() - 0.5) * 0.18,
    }));
  }

  function tick() {
    ctx.clearRect(0, 0, width, height);
    nodes.forEach((n) => {
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 0 || n.x > width) n.vx *= -1;
      if (n.y < 0 || n.y > height) n.vy *= -1;
    });

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < LINK_DIST) {
          ctx.strokeStyle = "rgba(212, 175, 55, " + (0.2 * (1 - dist / LINK_DIST)) + ")";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
    }
    nodes.forEach((n) => {
      ctx.fillStyle = "rgba(233, 208, 140, 0.6)";
      ctx.beginPath();
      ctx.arc(n.x, n.y, 1.6, 0, Math.PI * 2);
      ctx.fill();
    });

    requestAnimationFrame(tick);
  }

  resize();
  initNodes();
  tick();
  window.addEventListener("resize", () => { resize(); });
})();
