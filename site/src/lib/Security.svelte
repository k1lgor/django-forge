<script>
  import { SECURITY_CHECKS } from "./forge-data.js";

  let open = $state(null);
</script>

<section class="security" id="security">
  <h2 class="sec-title">production-ready <span class="c-accent">by default</span></h2>
  <p class="sub c-dim">claims you can verify — every one is true of a freshly forged project.</p>

  <ul class="checks">
    {#each SECURITY_CHECKS as check, i}
      <li>
        <button class="row" onclick={() => (open = open === i ? null : i)} aria-expanded={open === i}>
          <span class="ok" aria-hidden="true">✓</span>
          <span class="claim">{check.claim}</span>
          <span class="chev c-dim">{open === i ? "▾" : "▸"}</span>
        </button>
        {#if open === i}
          <p class="detail">{check.detail}</p>
        {/if}
      </li>
    {/each}
  </ul>
</section>

<style>
  .security { max-width: 1080px; margin: 0 auto; padding: 3rem 1.25rem 0.5rem; }
  .sec-title {
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: clamp(1.1rem, 2.4vw, 1.5rem); color: #ffe9c9;
    margin-bottom: 0.4rem;
  }
  .c-accent { color: #ff8a3d; }
  .c-dim { color: #5c6a82; }
  .sub { margin: 0 0 1.4rem; font-size: 0.9rem; }

  .checks { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.6rem; }
  .checks li {
    background: #0e1219; border: 1px solid #232a3a; border-radius: 10px; overflow: hidden;
  }
  .row {
    width: 100%; background: none; border: none; cursor: pointer;
    display: grid; grid-template-columns: auto 1fr auto; gap: 0.7rem;
    align-items: center; padding: 0.85rem 1rem; text-align: left;
    font: inherit; color: #e8eef8;
  }
  .ok { color: #3ddc84; font-weight: 700; }
  .chev { justify-self: end; }
  .detail {
    margin: 0; padding: 0 1rem 1rem 2.4rem; color: #9aa7bd; font-size: 0.88rem; line-height: 1.55;
  }
</style>
