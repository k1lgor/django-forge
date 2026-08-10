<script>
  import { FRAMEWORKS, DATABASES, LAYERS, buildFileSet, INSTALL_CMD } from "./forge-data.js";

  let framework = $state("drf");
  let database = $state("postgres");
  let selected = $state(["docker", "celery", "healthcheck", "audit", "backup", "seed", "preflight"]);
  let phase = $state("idle"); // idle | forging | done
  let t0 = $state(0);
  let elapsed = $state(0);
  let visibleFiles = $state([]); // {path, source, lines, revealed}
  let currentFile = $state(null);
  let typedLine = $state("");
  let timerId = null;

  function toggleLayer(id) {
    selected = selected.includes(id) ? selected.filter((l) => l !== id) : [...selected, id];
  }

  function startForge() {
    if (phase === "forging") return;
    const files = buildFileSet({ framework, database, layers: selected });
    phase = "forging";
    t0 = performance.now();
    elapsed = 0;
    visibleFiles = [];
    currentFile = null;
    typedLine = "";
    clearInterval(timerId);
    timerId = setInterval(tick, 80);
    forge(files, 0, performance.now());
  }

  function forge(files, index, start) {
    if (index >= files.length) {
      finishForge();
      return;
    }
    const file = files[index];
    const dur = 550 + Math.min(file.lines.join("\n").length * 26, 1600);
    const revealAt = start + 200;
    currentFile = file;
    typedLine = "";
    const reveal = () => {
      typedLine = file.lines.join("\n").slice(0, Math.max(0, (performance.now() - revealAt) / 22));
      if (performance.now() - revealAt < file.lines.join("\n").length * 22) {
        requestAnimationFrame(reveal);
      } else {
        typedLine = file.lines.join("\n");
        visibleFiles = visibleFiles.map((f, i) =>
          i === visibleFiles.length - 1 ? { ...f, revealed: true } : f,
        );
        requestAnimationFrame(() => forge(files, index + 1, performance.now()));
      }
    };
    setTimeout(() => {
      visibleFiles = [...visibleFiles, { ...file, revealed: false }];
      requestAnimationFrame(reveal);
    }, Math.min(650, 420 + file.lines.join("\n").length * 18));
  }

  function finishForge() {
    phase = "done";
    clearInterval(timerId);
  }

  function tick() {
    elapsed = Math.min((performance.now() - t0) / 1000, 25);
    if (phase === "done") clearInterval(timerId);
  }

  function fmt(s) {
    const m = Math.floor(s / 60);
    const ss = Math.floor(s % 60);
    return `${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  }

  const stopwatch = $derived(fmt(phase === "done" ? Math.min(elapsed + 0.4, 25) : elapsed));
</script>

<section class="sim" id="forge-wizard">
  <h2 class="sec-title">try the forge <span class="c-dim">— pick, press run, watch it build</span></h2>

  <div class="panel">
    <div class="control">
      <fieldset>
        <legend>api framework</legend>
        <div class="opts">
          {#each FRAMEWORKS as f}
            <button class:on={framework === f.id} onclick={() => (framework = f.id)}>{f.name}</button>
          {/each}
        </div>
      </fieldset>
      <fieldset>
        <legend>database</legend>
        <div class="opts">
          {#each DATABASES as d}
            <button class:on={database === d.id} onclick={() => (database = d.id)}>{d.name}</button>
          {/each}
        </div>
      </fieldset>
      <fieldset>
        <legend>optional layers <span class="c-dim">({selected.length})</span></legend>
        <div class="chips">
          {#each LAYERS as layer}
            <button
              class="chip"
              class:on={selected.includes(layer.id)}
              onclick={() => toggleLayer(layer.id)}
              title={layer.tagline}
            >{layer.name}</button>
          {/each}
        </div>
      </fieldset>
      <div class="actions">
        <button class="run" onclick={startForge} disabled={phase === "forging"}>
          {phase === "done" ? "re-forge" : phase === "forging" ? "forging…" : "⚒ forge it"}
        </button>
        <span class="watch">⏱ {stopwatch}</span>
      </div>
    </div>

    <div class="stage">
      <div class="tree" aria-label="generated project tree">
        <div class="stage-head c-dim">myproject/</div>
        {#each visibleFiles as f}
          <div class="frow" class:new={f.revealed}>
            <span class="mark">{f.revealed ? "+" : "·"}</span>
            <span class="fpath">{f.path}</span>
          </div>
        {/each}
        {#if phase === "idle"}
          <div class="empty c-dim">— choose your stack and hit “forge it” —</div>
        {/if}
      </div>
      <div class="term" aria-label="terminal output">
        {#if currentFile}
          <span class="c-cyan">$ touch {currentFile.path}</span>
          <pre>{typedLine}</pre>
        {:else if phase === "done"}
          <span class="done">Project forged successfully!</span>
        {:else}
          <span class="c-dim">awaiting forge…</span>
        {/if}
      </div>
    </div>
  </div>

  <p class="hint">
    this is the real artifact map — every file appears because the actual templates generate it. <br>
    install it yourself: <code>{INSTALL_CMD}</code>
  </p>
</section>

<style>
  .sim { max-width: 1080px; margin: 0 auto; padding: 3rem 1.25rem 1rem; }
  .sec-title {
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: clamp(1.1rem, 2.4vw, 1.5rem);
    color: #ffe9c9; margin-bottom: 1.25rem; letter-spacing: 0.02em;
  }
  .c-dim { color: #5c6a82; }
  .panel {
    display: grid; gap: 1.25rem;
    grid-template-columns: minmax(260px, 1fr) 1.6fr;
  }
  @media (max-width: 760px) { .panel { grid-template-columns: 1fr; } }

  .control {
    background: #0e1219; border: 1px solid #232a3a; border-radius: 10px;
    padding: 1.1rem 1.2rem; display: flex; flex-direction: column; gap: 1rem;
  }
  fieldset { border: none; padding: 0; margin: 0; }
  legend {
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
    color: #ff8a3d; margin-bottom: 0.5rem;
  }
  .opts { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .opts button {
    background: #141a26; color: #9aa7bd; border: 1px solid #2a3446;
    border-radius: 6px; padding: 0.35rem 0.75rem; cursor: pointer;
    font: inherit; font-size: 0.82rem;
  }
  .opts button.on { border-color: #ff8a3d; color: #ffd84d; box-shadow: 0 0 10px rgba(255, 138, 61, 0.15); }

  .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .chip {
    background: #141a26; color: #5c6a82; border: 1px solid #232a3a;
    border-radius: 999px; padding: 0.22rem 0.7rem; cursor: pointer;
    font: inherit; font-size: 0.74rem;
  }
  .chip.on { color: #38e1e1; border-color: #38e1e1; }

  .actions { display: flex; align-items: center; gap: 1rem; margin-top: 0.25rem; }
  .run {
    background: linear-gradient(135deg, #ff8a3d, #ff4d2e); color: #1a0e06;
    border: none; border-radius: 8px; padding: 0.6rem 1.3rem; cursor: pointer;
    font: inherit; font-weight: 700; letter-spacing: 0.04em;
  }
  .run:hover { filter: brightness(1.1); }
  .run:disabled { opacity: 0.6; cursor: wait; }
  .watch { font-family: ui-monospace, Menlo, Consolas, monospace; color: #38e1e1; font-size: 0.9rem; }

  .stage {
    display: grid; gap: 1rem; grid-template-rows: auto 1fr;
  }
  .tree, .term {
    background: #0a0d13; border: 1px solid #232a3a; border-radius: 10px;
    padding: 1rem 1.15rem; font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 0.8rem; line-height: 1.7; overflow-x: auto;
  }
  .stage-head { color: #5c6a82; }
  .frow { display: flex; gap: 0.6rem; color: #c6d0e0; }
  .frow.new .fpath { color: #3ddc84; }
  .mark { color: #3ddc84; }
  .frow:not(.new) .mark { color: #5c6a82; }
  .empty { padding: 0.5rem 0; }

  .term { min-height: 120px; white-space: pre; }
  .term .done {
    color: #ff8a3d; font-weight: 700; font-size: 1rem;
    text-shadow: 0 0 18px rgba(255, 77, 46, 0.5);
  }
  .hint { margin-top: 0.9rem; font-size: 0.78rem; color: #5c6a82; }
  .hint code {
    background: #141a26; border: 1px solid #232a3a; padding: 0.1rem 0.4rem;
    border-radius: 5px; color: #ffd84d;
  }
</style>
