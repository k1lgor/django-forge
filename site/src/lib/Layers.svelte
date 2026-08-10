<script>
  import { LAYERS } from "./forge-data.js";

  let open = $state(null);
  let closeBtn = $state(null);

  const activeLayer = $derived(LAYERS.find((l) => l.id === open) ?? null);

  function openCard(id) {
    open = id;
  }

  function closeCard() {
    open = null;
  }

  // ESC closes; body scroll is locked while the pop-up is open
  $effect(() => {
    if (open !== null) {
      document.body.style.overflow = "hidden";
      const onKey = (e) => {
        if (e.key === "Escape") closeCard();
      };
      window.addEventListener("keydown", onKey);
      return () => {
        document.body.style.overflow = "";
        window.removeEventListener("keydown", onKey);
      };
    }
  });

  // focus the close button when the pop-up opens
  $effect(() => {
    if (open !== null && closeBtn) closeBtn.focus();
  });
</script>

<section class="layers" id="layers">
  <h2 class="sec-title">eleven layers of <span class="c-accent">production-ready</span></h2>
  <p class="sub c-dim">every card opens to the real files that layer adds to your scaffold.</p>

  <div class="grid">
    {#each LAYERS as layer}
      <button class="ingot" onclick={() => openCard(layer.id)} aria-haspopup="dialog">
        <span class="flame" aria-hidden="true">▮</span>
        <span class="id">
          <span class="name">{layer.name}</span>
          <span class="tag c-dim">{layer.tagline}</span>
        </span>
        <span class="chev c-dim" aria-hidden="true">+</span>
      </button>
    {/each}
  </div>
</section>

{#if activeLayer}
  <div class="backdrop" onclick={closeCard} role="presentation">
    <div
      class="modal"
      role="dialog"
      aria-modal="true"
      aria-label={activeLayer.name}
      onclick={(e) => e.stopPropagation()}
    >
      <div class="mhead">
        <span class="flame" aria-hidden="true">▮</span>
        <span class="mname">{activeLayer.name}</span>
        <span class="chev c-dim">{activeLayer.tagline}</span>
        <button class="x" bind:this={closeBtn} onclick={closeCard} aria-label="close">✕</button>
      </div>
      <div class="body">
        {#each activeLayer.files as f}
          <div class="file">
            <div class="fpath c-cyan">{f.path}</div>
            <pre>{#each f.lines as l}<span>{l}
</span>{/each}</pre>
          </div>
        {/each}
        <div class="dep c-dim">dep: {activeLayer.dep}</div>
      </div>
    </div>
  </div>
{/if}

<style>
  .layers { max-width: 1080px; margin: 0 auto; padding: 3rem 1.25rem 0.5rem; }
  .sec-title {
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: clamp(1.1rem, 2.4vw, 1.5rem); color: #ffe9c9;
    margin-bottom: 0.4rem; letter-spacing: 0.02em;
  }
  .c-accent { color: #ff8a3d; }
  .c-dim { color: #5c6a82; }
  .c-cyan { color: #38e1e1; }
  .sub { margin: 0 0 1.4rem; font-size: 0.9rem; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.85rem; }
  .ingot {
    background: #0e1219; border: 1px solid #232a3a; border-radius: 10px;
    cursor: pointer; text-align: left; font: inherit; color: #e8eef8;
    display: grid; grid-template-columns: auto 1fr auto; gap: 0.6rem;
    align-items: center; padding: 0.9rem 1rem;
    transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
  }
  .ingot:hover {
    border-color: #ff8a3d; transform: translateY(-2px);
    box-shadow: 0 8px 24px -12px rgba(255, 138, 61, 0.35);
  }
  .ingot:focus-visible { outline: 2px solid #ff8a3d; outline-offset: 2px; }
  .flame { color: #ff8a3d; font-size: 0.85rem; }
  .id { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
  .name { font-weight: 700; letter-spacing: 0.02em; }
  .tag { font-size: 0.75rem; line-height: 1.35; }
  .chev { justify-self: end; color: #3a4458; font-size: 1rem; font-weight: 700; }
  .ingot:hover .chev { color: #ff8a3d; }

  .backdrop {
    position: fixed; inset: 0; z-index: 60;
    background: rgba(4, 6, 10, 0.82); backdrop-filter: blur(5px);
    display: grid; place-items: center; padding: 1.25rem;
    animation: fadein 0.18s ease-out;
  }
  .modal {
    width: min(720px, 100%); max-height: min(82vh, 100%);
    background: #0e1219; border: 1px solid #ff8a3d33; border-radius: 14px;
    box-shadow: 0 0 0 1px rgba(255, 138, 61, 0.06), 0 40px 120px -30px rgba(0, 0, 0, 0.9);
    display: flex; flex-direction: column; overflow: hidden;
    animation: pop 0.22s cubic-bezier(0.2, 1.2, 0.3, 1);
  }
  .mhead {
    display: grid; grid-template-columns: auto auto 1fr auto; gap: 0.6rem;
    align-items: baseline; padding: 1rem 1.2rem;
    border-bottom: 1px solid #1c2230;
  }
  .mname { font-weight: 700; font-size: 1.05rem; color: #ffe9c9; }
  .x {
    background: none; border: 1px solid #2a3446; color: #9aa7bd; cursor: pointer;
    border-radius: 6px; width: 1.9rem; height: 1.9rem; font: inherit;
    justify-self: end; align-self: center;
  }
  .x:hover { color: #ff8a3d; border-color: #ff8a3d; }

  .body {
    padding: 1rem 1.2rem 1.2rem; overflow-y: auto;
    display: flex; flex-direction: column; gap: 0.7rem;
  }
  .file { background: #0a0d13; border: 1px solid #1c2230; border-radius: 8px; padding: 0.6rem 0.8rem; }
  .fpath { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.75rem; margin-bottom: 0.3rem; }
  pre {
    margin: 0; font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 0.72rem; color: #9aa7bd; overflow-x: auto; white-space: pre;
  }
  .dep { font-size: 0.72rem; }

  @keyframes fadein { from { opacity: 0; } }
  @keyframes pop {
    from { opacity: 0; transform: scale(0.92) translateY(10px); }
    to { opacity: 1; transform: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    .backdrop, .modal { animation: none; }
  }
</style>
