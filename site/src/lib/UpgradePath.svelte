<script>
  import { UPGRADE_STATES } from "./forge-data.js";
</script>

<section class="upgrade" id="upgrade">
  <h2 class="sec-title">your edits <span class="c-accent">survive</span></h2>
  <p class="sub c-dim">
    forge writes a manifest (`.forge-manifest.json`) hashing every file it produces. <br>
    on <code>forge add</code>/<code>forge upgrade</code>, pristine files are refreshed —
    files you modified are skipped, byte for byte.
  </p>

  <div class="rows">
    {#each UPGRADE_STATES as s}
      <div class="row">
        <code class="fpath">{s.file}</code>
        <span class="state {s.state}">{s.state}</span>
        <span class="arrow">→</span>
        <span class="state {s.outcome}">{s.outcome}</span>
        <span class="note c-dim">{s.note}</span>
      </div>
    {/each}
  </div>
</section>

<style>
  .upgrade { max-width: 1080px; margin: 0 auto; padding: 3rem 1.25rem 0.5rem; }
  .sec-title {
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: clamp(1.1rem, 2.4vw, 1.5rem); color: #ffe9c9;
    margin-bottom: 0.4rem;
  }
  .c-accent { color: #ff8a3d; }
  .c-dim { color: #5c6a82; }
  .sub { margin: 0 0 1.4rem; font-size: 0.9rem; line-height: 1.6; }
  .sub code {
    background: #141a26; border: 1px solid #232a3a; padding: 0.05rem 0.35rem;
    border-radius: 4px; color: #38e1e1; font-size: 0.8rem;
  }

  .rows { display: flex; flex-direction: column; gap: 0.6rem; }
  .row {
    display: grid; grid-template-columns: auto auto auto auto 1fr; gap: 0.8rem;
    align-items: center; background: #0e1219; border: 1px solid #232a3a;
    border-radius: 10px; padding: 0.8rem 1rem;
  }
  @media (max-width: 720px) {
    .row { grid-template-columns: 1fr auto auto; }
    .note { grid-column: 1 / -1; }
  }
  .fpath { color: #38e1e1; font-size: 0.82rem; }
  .state { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
  .state.pristine { color: #3ddc84; }
  .state.modified { color: #ffd84d; }
  .state.upgraded { color: #3ddc84; }
  .state.skipped { color: #ff8a3d; }
  .arrow { color: #5c6a82; }
  .note { font-size: 0.82rem; }
</style>
