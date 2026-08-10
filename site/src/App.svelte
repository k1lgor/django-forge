<script>
  import BootTerminal from "./lib/BootTerminal.svelte";
  import ForgeSim from "./lib/ForgeSim.svelte";
  import Layers from "./lib/Layers.svelte";
  import Security from "./lib/Security.svelte";
  import UpgradePath from "./lib/UpgradePath.svelte";
  import { INSTALL_CMD, RUN_CMD, FORGE_VERSION } from "./lib/forge-data.js";

  let copied = $state(false);

  async function copyInstall() {
    try {
      await navigator.clipboard.writeText(INSTALL_CMD);
      copied = true;
      setTimeout(() => (copied = false), 1800);
    } catch {
      copied = false;
    }
  }

  function handleBoot() {
    document.getElementById("forge-wizard")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
</script>

<svelte:head>
  <title>django-forge 🔨 — scaffold production-ready Django projects</title>
  <meta name="description" content="Ask 3 questions. Get a production-ready Django project — custom user model, allauth, Docker, Celery, S3, health checks and more. One command, under a minute." />
</svelte:head>

<header class="nav">
  <a class="brand" href="#boot"><span class="flame">▮</span> django-forge <span class="ver c-dim">v{FORGE_VERSION}</span></a>
  <nav>
    <a href="#forge-wizard">forge</a>
    <a href="#layers">layers</a>
    <a href="#security">security</a>
    <a href="#upgrade">upgrade</a>
    <a class="gh" href="https://github.com/k1lgor/django-forge" target="_blank" rel="noopener">github ↗</a>
  </nav>
</header>

<BootTerminal onStart={handleBoot} />

<main>
  <section class="hero" id="boot">
    <h1>Forge your Django project.</h1>
    <p class="lead c-dim">
      Ask <strong>3 questions</strong> — get a <strong>production-ready</strong> Django project,
      custom user model, allauth, tooling, CI and 11 optional layers. One command, under a minute.
    </p>
    <div class="install">
      <code class="cmd"><span class="c-dim">$</span> {INSTALL_CMD}</code>
      <button onclick={copyInstall}>{copied ? "✓ copied" : "copy"}</button>
    </div>
    <p class="run c-dim">then: <code>{RUN_CMD}</code></p>
  </section>

  <ForgeSim />

  <div class="band">
    <p class="band-line">wizard → <span class="c-yellow">render</span> → <span class="c-cyan">uv sync</span> → <span class="c-cyan">migrate</span> → <span class="c-accent">check --deploy</span> → <span class="c-green">forged</span></p>
  </div>

  <Layers />
  <Security />
  <UpgradePath />

  <section class="cta">
    <h2>Ready to forge?</h2>
    <div class="install">
      <code class="cmd"><span class="c-dim">$</span> {INSTALL_CMD}</code>
      <button onclick={copyInstall}>{copied ? "✓ copied" : "copy"}</button>
    </div>
    <p class="run c-dim">MIT licensed · built with Django best practices</p>
  </section>
</main>

<footer class="footer c-dim">
  <span>django-forge v{FORGE_VERSION}</span>
  <span>·</span>
  <a href="https://github.com/k1lgor/django-forge" target="_blank" rel="noopener">source on github</a>
</footer>

<style>
  .nav {
    position: sticky; top: 0; z-index: 20;
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.8rem 1.5rem;
    background: rgba(10, 13, 19, 0.85); backdrop-filter: blur(8px);
    border-bottom: 1px solid #1c2230;
  }
  .brand { font-weight: 700; color: #ffe9c9; text-decoration: none; letter-spacing: 0.02em; }
  .flame { color: #ff8a3d; }
  .ver { font-size: 0.7rem; font-weight: 400; }
  nav { display: flex; gap: 1.1rem; }
  nav a { color: #9aa7bd; text-decoration: none; font-size: 0.85rem; }
  nav a:hover { color: #ffd84d; }
  nav .gh { color: #38e1e1; }
  @media (max-width: 640px) { nav { gap: 0.7rem; } nav a:not(.gh) { display: none; } }

  .hero { max-width: 1080px; margin: 0 auto; padding: 3.5rem 1.25rem 0.5rem; text-align: center; }
  .hero h1 {
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: clamp(2rem, 6vw, 3.6rem); margin: 0 0 1rem;
    color: #fff3e0; letter-spacing: 0.01em;
    text-shadow: 0 0 40px rgba(255, 138, 61, 0.25);
  }
  .hero .lead { font-size: clamp(1rem, 2vw, 1.2rem); max-width: 640px; margin: 0 auto 1.8rem; line-height: 1.6; }
  .hero strong { color: #ffd84d; font-weight: 600; }

  .install { display: flex; justify-content: center; gap: 0.7rem; align-items: center; }
  .cmd {
    background: #0a0d13; border: 1px solid #2a3446; border-radius: 8px;
    padding: 0.7rem 1.1rem; color: #ffd84d; font-size: 0.95rem;
    box-shadow: 0 0 24px rgba(255, 138, 61, 0.08);
  }
  .install button {
    background: linear-gradient(135deg, #ff8a3d, #ff4d2e); color: #1a0e06;
    border: none; border-radius: 8px; padding: 0.7rem 1.1rem; cursor: pointer;
    font: inherit; font-weight: 700;
  }
  .install button:hover { filter: brightness(1.1); }
  .hero .run { margin-top: 0.9rem; font-size: 0.85rem; }
  .run code {
    background: #141a26; border: 1px solid #232a3a; padding: 0.05rem 0.4rem;
    border-radius: 4px; color: #38e1e1; font-size: 0.8rem;
  }
  .c-dim { color: #5c6a82; }
  .c-yellow { color: #ffd84d; }
  .c-cyan { color: #38e1e1; }
  .c-accent { color: #ff8a3d; }
  .c-green { color: #3ddc84; }

  .band { max-width: 1080px; margin: 0 auto; padding: 1.5rem 1.25rem 0; }
  .band-line {
    text-align: center; font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 0.78rem; color: #9aa7bd; letter-spacing: 0.05em;
    border-top: 1px dashed #1c2230; border-bottom: 1px dashed #1c2230; padding: 0.7rem 0;
  }

  .cta { text-align: center; padding: 3.5rem 1.25rem 2.5rem; }
  .cta h2 {
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: clamp(1.5rem, 4vw, 2.4rem); color: #ffe9c9; margin-bottom: 1.4rem;
  }
  .cta .run { margin-top: 1rem; font-size: 0.8rem; }

  .footer {
    display: flex; justify-content: center; gap: 0.7rem; align-items: center;
    padding: 1.5rem; border-top: 1px solid #1c2230; font-size: 0.78rem;
  }
  .footer a { color: #38e1e1; text-decoration: none; }
  .footer a:hover { color: #ffd84d; }
</style>
