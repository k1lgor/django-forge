<script>
  import { BOOT_LINES } from "./forge-data.js";

  let { onStart = () => {} } = $props();

  const reduced = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const bootedOnce = typeof sessionStorage !== "undefined" && sessionStorage.getItem("forge-booted") === "1";

  // typewriter: chars revealed across the banner + tagline lines
  let typed = $state(reduced || bootedOnce ? 9999 : 0);
  let started = $state(reduced || bootedOnce);
  const animate = !reduced && !bootedOnce;

  const bannerLen = BOOT_LINES[0].text.length + 1; // + newline
  const taglineLen = BOOT_LINES[1].text.length;
  const total = bannerLen + taglineLen;

  const bannerText = $derived(
    BOOT_LINES[0].text.slice(0, Math.min(typed, BOOT_LINES[0].text.length)),
  );
  const taglineText = $derived(
    BOOT_LINES[1].text.slice(0, Math.max(0, Math.min(taglineLen, typed - bannerLen))),
  );
  const typing = $derived(typed < total);

  function go() {
    typed = 9999;
    started = true;
    try {
      sessionStorage.setItem("forge-booted", "1");
    } catch {}
    onStart();
  }

  // auto-complete ends the animation without forcing a scroll
  $effect(() => {
    if (!animate || started) return;
    const id = setInterval(() => {
      typed = Math.min(total, typed + 3);
      if (typed >= total) {
        clearInterval(id);
        setTimeout(() => {
          typed = 9999;
          started = true;
          try {
            sessionStorage.setItem("forge-booted", "1");
          } catch {}
        }, 400);
      }
    }, 26);
    return () => clearInterval(id);
  });

  // "press any key to skip" — only active while the boot is running
  $effect(() => {
    if (!animate) return;
    const onKey = () => {
      if (!started) go();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
</script>

<section class="boot" id="boot" aria-label="forge boot sequence">
  <div class="term" role="img" aria-label="terminal boot sequence">
    <span class="type c-cyan">{bannerText}{#if typing && bannerText.length < BOOT_LINES[0].text.length}<span class="cursor">▍</span>{/if}</span>
    <span class="type c-dim">{taglineText}{#if typing && taglineText.length === taglineLen}<span class="cursor">▍</span>{/if}</span>
    {#each BOOT_LINES.slice(2) as line, i (line.text ?? line.label)}
      {#if line.kind === "led"}
        <span class="led-row" style="--i: {i}"><span class="led" class:on={started}></span><span class="c-dim">[ {started ? line.ok : "..."} ]</span><span class="c-yellow">{line.label}</span></span>
      {:else if line.kind === "prompt"}
        <span class="prompt" class:on={started}><button onclick={go}>▶ press start</button></span>
      {/if}
    {/each}
  </div>
  <p class="hint">press any key to skip — the forge is below</p>
</section>

<style>
  .boot {
    max-width: 920px;
    margin: 0 auto;
    padding: clamp(1.5rem, 5vw, 4.5rem) 1.25rem 0;
  }
  .term {
    background: #0a0d13;
    border: 1px solid #232a3a;
    border-radius: 10px;
    box-shadow:
      0 0 0 1px rgba(255, 138, 61, 0.06),
      0 20px 60px -20px rgba(0, 0, 0, 0.8),
      inset 0 0 80px rgba(255, 138, 61, 0.03);
    padding: 1.1rem 1.4rem;
    font-family: ui-monospace, "Cascadia Code", "JetBrains Mono", Menlo, Consolas, monospace;
    font-size: clamp(0.72rem, 1.5vw, 0.92rem);
    line-height: 1.45;
    overflow-x: auto;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    color: #9aa7bd;
  }
  .type { white-space: pre; }
  .c-cyan { color: #38e1e1; }
  .c-yellow { color: #ffd84d; }
  .c-dim { color: #5c6a82; }

  .cursor { color: #38e1e1; animation: blink 1s steps(2, jump-none) infinite; }

  .led-row { display: flex; gap: 0.6rem; align-items: center; }
  .led {
    width: 8px; height: 8px; border-radius: 50%;
    background: #2a3446; flex: none;
    opacity: 0;
    animation: ledin 0.25s ease-out forwards;
    animation-delay: calc(0.5s + var(--i) * 0.12s);
  }
  .led.on { background: #3ddc84; box-shadow: 0 0 8px #3ddc84; }

  .prompt { display: block; }
  .prompt button {
    background: none; border: 1px solid #3a4458; border-radius: 6px;
    padding: 0.45rem 1rem; cursor: pointer;
    font: inherit; color: #ffd84d; letter-spacing: 0.12em;
    animation: blink 1.1s steps(2, jump-none) infinite;
  }
  .prompt button:hover { border-color: #ffd84d; background: rgba(255, 216, 77, 0.06); }
  .prompt.on button { animation: none; color: #3ddc84; border-color: #3ddc84; }

  .hint {
    text-align: center; margin-top: 0.9rem;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 0.7rem; color: #5c6a82; letter-spacing: 0.08em;
  }

  @keyframes blink { 50% { opacity: 0; } }
  @keyframes ledin { from { opacity: 0; transform: scale(0.4); } to { opacity: 1; transform: scale(1); } }

  @media (prefers-reduced-motion: reduce) {
    .prompt button, .cursor { animation: none; }
  }
</style>
