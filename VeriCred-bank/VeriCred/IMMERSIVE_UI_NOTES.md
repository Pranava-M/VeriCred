# Immersive Intro + Themed Portal — Implementation Notes

## Architecture decision (read this first)

Your app is **Flask + Jinja2** (server-rendered HTML), not React. The
original spec asked for Framer Motion, which is React-only. Rather than
rewrite your whole backend into a React SPA (weeks of work, and would mean
throwing away your working Flask routes/blockchain integration), everything
below uses **vanilla Three.js + GSAP + Lenis** — same visual result, zero
framework rewrite. If you later want a full React rebuild, this is still a
reasonable stepping stone: the animation logic ports over conceptually.

## What was built

| File | Purpose |
|---|---|
| `templates/intro.html` | The new landing page (route `/`) — hosts the 3D scene |
| `static/js/intro.js` | Three.js scene: building, watchman, scroll camera, door, vault loader |
| `static/css/intro.css` | Intro-specific styling |
| `templates/base.html` | Updated — expanded nav, ambient background, Lenis, page transitions |
| `static/js/ambient.js` | The "something running in the background" nav animation |
| `static/js/page-fx.js` | Site-wide Lenis smooth scroll + fade transitions + nav dropdown |
| `static/css/style.css` | Re-themed to a calm cool teal/cyan palette |
| `templates/placeholder.html` | Shared template for the new header sections |
| `app.py` | Dashboard moved to `/portal`; `/` now serves the intro; 6 new placeholder routes added |

## Step-by-step: how the intro sequence works

1. **Scene setup** — `THREE.Scene`, a `PerspectiveCamera`, lighting (hemisphere
   + directional "sun" + a pulsing point light at the door for a glow).
2. **Building geometry** — built entirely from primitives (no external 3D
   model files): `BoxGeometry` for the body, a 3-sided `CylinderGeometry`
   rotated flat for the triangular pediment roof, thin cylinders for
   columns, plane geometries for windows. This gives a stylized, low-poly
   aesthetic (flat-shaded materials) rather than a photoreal render.
3. **Watchman** — a simple humanoid built the same way (cylinder torso/legs,
   sphere head), with a subtle idle bob via `Math.sin()` each frame.
4. **Scroll-driven camera** — a tall invisible spacer div (`#scrollSpacer`,
   400vh) gives the page scroll distance. `GSAP ScrollTrigger` with
   `scrub: 1` ties camera position directly to scroll progress — scrolling
   down moves the camera from a wide establishing shot to right in front
   of the door.
5. **Door opening** — two `THREE.Group` pivots positioned at each door's
   hinge edge; rotating the pivot (not the mesh directly) makes the door
   swing open around its edge instead of its center — this is the standard
   Three.js hinge technique.
6. **Vault loader** — triggered once scroll reaches the end. A plain
   CSS/SVG spinner (not a Lottie file — see note below) plus a GSAP-driven
   percentage counter, then redirects to `/portal`.
7. **Session-aware skip** — `sessionStorage` remembers the visitor has seen
   the intro, so it only plays once per browser session, not on every
   visit to `/`. There's also a visible "Skip intro" button — for an
   internal tool used daily, forcing the full animation every time would
   hurt usability, so this was a deliberate UX call.

### On Lottie specifically
The spec asked for Lottie for the loader. Lottie files are normally
exported from After Effects — there isn't one to hand-write from scratch,
and pulling in a random public Lottie JSON risks it silently breaking your
build later. The vault loader instead uses a lightweight CSS/SVG spinner
that achieves the same "vault unlocking" feeling with zero external
dependency risk. If you have (or purchase) an actual Lottie vault/lock
animation file, swap it in easily:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js"></script>
<script>
  lottie.loadAnimation({
    container: document.getElementById('vaultOverlay'),
    path: '/static/lottie/vault-unlock.json',
    autoplay: true, loop: false,
  });
</script>
```

## Reusable component suggestions (for building out the 6 new sections)

The `placeholder.html` template is intentionally generic — it's your
starting point for each of the 6 new sections. Recommended structure as
you build each one out:

- **Accounts Management / Transactions** — reuse `card-stats` grid pattern
  already used on the dashboard cards (`.card-stats`) for summary numbers,
  plus a data table using the same `.panel` + `.kv-row` styles from
  `detail.html` for row-level data.
- **Reports & Analytics** — reuse the Chart.js setup pattern from
  `detail.html`'s analytics section; wrap each chart in `.chart-card` for
  consistent styling.
- **Settings & Security** — form inputs should reuse `.edit-loan-form input`
  styling for consistency with the existing loan-amount editor.
- Add `class="glow-hover"` to any new card component to get the cool-cyan
  hover glow automatically — it's a drop-in utility class now defined in
  `style.css`.

## Performance best practices applied / recommended

**Applied already:**
- Low polygon counts throughout (columns use 10 radial segments, not 32;
  spheres use 10x10 segments) — keeps the WebGL scene light
- `renderer.setPixelRatio(Math.min(devicePixelRatio, 2))` — caps rendering
  resolution on high-DPI screens instead of rendering at full 3x/4x pixel
  density, which is a common accidental performance killer
- Ambient background canvas is scoped to just the nav bar's pixel area, not
  the full viewport — far cheaper to animate every frame
- `sessionStorage` skip — avoids re-loading the whole Three.js scene +
  assets on every single page visit during a work session

**Recommended as you build further:**
- **Lazy-load Three.js only on `/`** — it's currently loaded only on
  `intro.html`, not on every portal page (already done correctly — don't
  add the Three.js `<script>` tag to `base.html`)
- **Compress/minify** the CDN scripts are already minified (`.min.js`); if
  you self-host any assets later, run them through a minifier
- **Texture/asset compression** — if you later swap in real `.glb` 3D
  models (e.g., from Sketchfab or Mixamo) instead of primitive geometry,
  use `.glb` (binary, compressed) not `.gltf`+separate textures, and run
  models through `gltf-transform` or Blender's built-in glTF compression
  before adding them
- **Reduce ScrollTrigger recalculation cost** — if you add more
  scroll-triggered elements later, batch them under one `ScrollTrigger`
  timeline where possible rather than creating many independent triggers
