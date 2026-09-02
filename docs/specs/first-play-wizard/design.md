# First-play wizard — design

Line numbers reference `game.html` as of this reading (3,245 lines, HEAD at spec time).
They will drift; the search anchors given with each one are the durable reference.

## Overview

One new full-screen overlay, `#wizard`, built on the `#prefs` pattern: a fixed,
`inset:0` element with safe-area padding, toggled via the `hidden` attribute
(`#prefs` CSS at lines 47–61; markup at 487–493; open/close wiring at 3205–3208).
All logic lives in one new IIFE near the existing "Boot screen and preferences" IIFE
(lines 3140–3209), plus one CSS block and one HTML block. No game logic is touched.

## Storage

- **Key:** `craps.wizard.seen`, value `'1'`, read/written via `SecureStore`
  (line 1522) — Capacitor `Preferences` (iOS Keychain-backed prefs plugin) on device,
  localStorage on the web, same as `craps.consent` / `craps.dealer`.
- **Written when:** the wizard is dismissed by *any* route — Skip, Escape, Finish, or
  the error backstop. Never on show (an app killed mid-tour sees the tour again next
  launch, which is the desired behaviour for a tour someone didn't finish).
- **Never cleared** by the re-run control; re-run just shows the overlay again
  (the flag only gates the *automatic* first-launch showing).

### First-launch detection

```
firstLaunch = (craps.wizard.seen absent) AND (localStorage 'craps.view.v2' absent)
```

`craps.view.v2` is the layout-migration marker every existing install already has —
it is set unconditionally on every load (line 3124). It is therefore a perfect
"this device has run the app before" sentinel that grandfathers existing players
(R2) without a version dance.

**Ordering trap:** the viewmode IIFE (3113–3136) sets `craps.view.v2` during the same
page load, and the wizard's `SecureStore.get` is async. The wizard IIFE must snapshot
`localStorage.getItem('craps.view.v2')` **synchronously at IIFE start** into a local,
before awaiting anything. Placement of the wizard IIFE relative to line 3113 then
matters: put it **before** the viewmode IIFE in source order, or (simpler, chosen)
anywhere, but take the snapshot via a tiny synchronous statement hoisted above line
3113. Chosen design: add one line immediately before the viewmode IIFE —
`const WIZ_RETURNING = !!(function(){try{return localStorage.getItem('craps.view.v2')}catch(e){return null}})();`
— and have the wizard IIFE read `WIZ_RETURNING`.

## Step flow

```
boot fades (hide(), 3143) ──► maybeShowWizard()
                                   │ firstLaunch?
                          no ──────┴────── yes
                          done              ▼
        ┌───────────────────────────────────────────────┐
        │ 1 Welcome      basics: tap / long-press / roll │
        │ 2 Layout       List ◄─► Half table             │
        │ 3 Voice        recorded stickman on/off        │
        │ 4 AI           informational only              │
        │ 5 Finish       Preferences + re-run pointer    │
        └───────────────────────────────────────────────┘
   Back/Next between steps · "Skip tour" visible on 1–4 ·
   Esc = skip · Finish on 5 · every exit ⇒ seen='1'
```

- Steps are five `<section class="wiz-step">` siblings; exactly one lacks `hidden`.
  Navigation toggles `hidden` — no innerHTML rebuilding, no per-step state.
- A dot indicator (`● ○ ○ ○ ○`) shows position; Back is absent on step 1; Next
  becomes Finish on step 5.
- Re-run entry (from Preferences) calls the same `show(0)` function; steps 2/3 read
  current values at show-time (see below), so they reflect reality on re-run (R8).

### Step content and behaviour

**Step 1 — Welcome.** Static copy. Title reuses the boot identity ("Pass Line").
Body: play-money practice table, no real wagering, no chips for sale (consistent with
the privacy text's "Children" paragraph, lines 2540–2541). Basics reuse the `#hint`
wording family (line 591): tap to bet; place bets sit off on the come-out —
long-press (or right-click / W) a number to toggle working; Roll dice.

**Step 2 — Layout.** Two selectable option cards (radio-group semantics), List and
Half table, each with two lines of copy and a small pure-CSS thumbnail (stacked bars
for List; a green arc-and-boxes for felt — no images, keeps R3/R6). Copy notes the
felt view's one behavioural difference: odds are placed by clicking the pass line
again (comment at 3128–3129). On show, the current value of `#viewmode`
(line 577) pre-selects a card. Picking a card sets
`viewmode.value = v; viewmode.dispatchEvent(new Event('change'))` so the existing
`apply()` (3126–3132) runs: layout flips live behind the overlay and `craps.view`
persists. The wizard writes nothing itself (R7).

**Step 3 — Voice.** Copy: the dealer's roll calls are the developer's recorded
stickman clips shipped inside the app (`voice/*.mp3`, `Voice.call`, lines 1928–1945)
— free, offline, no AI involved. One toggle, default reflecting `DealerCfg.d.voice`
(default false, line 1849) read at show-time. Toggling sets the existing
`[data-d="voice"]` checkbox (line 721) and dispatches `change`, reusing the handler
at 2501–2516 — which saves `craps.dealer`, repaints the mic button, flashes, and
plays the local sample clip (`co11`, line 2514). The sample is the preview; the
wizard adds no audio code.

**Step 4 — AI, inform-don't-sell.** Static copy, no controls except Next/Back/Skip.
Content contract (each bullet is one short paragraph):
- The AI coach and the spoken-bet dealer are part of *Advanced*, a one-time unlock
  in the app stores. This wizard is not the place to buy it; AI setup in Preferences
  is where all of that lives.
- They run on **your own AI account**: an API key is a password-like code you create
  on a provider's website that lets apps use their AI and bills *you* directly.
  OpenRouter is the default (one key, many models — mirrors `PROVIDERS.openrouter`,
  lines 1569–1588); keys come from the provider's own site.
- Rough cost framing: pay-per-use, typically well under a cent per coach answer or
  dealer remark; there is no subscription and the developer receives nothing
  (mirrors lockbox copy, 686–687).
- Nothing is ever sent anywhere until you have added a key **and** ticked the
  consent disclosure in AI setup (`Consent`, lines 1713–1731; `AI.ready()` gates at
  1748–1758). Until then — and forever, if you never do — the entire game works
  offline: table, tracking, shooters, sessions, statistics.
No `#proBuy`-style button, no price, no store call, no key test (R6; A5).
Web build nuance (R4): copy says the features "are part of the Advanced unlock in
the app stores" — true on iOS, and merely descriptive on the web where `Pro.owned`
is already true (1676).

**Step 5 — Finish.** Points at the ⚙ button (`#prefsBtn`, line 575): layout, pace,
odds limit, voice, AI setup, and privacy details all live in Preferences. Mentions
"Show the welcome tour" there re-runs this. Finish button closes and marks seen.

## DOM and CSS

**Markup** — inserted after the `#prefs` block (after line 493), before `.wrap`:

```html
<div id="wizard" hidden role="dialog" aria-modal="true" aria-label="Welcome tour">
  <div class="wiz-body">
    <section class="wiz-step" data-step="0">…</section>
    … ×5 …
    <div class="wiz-dots" aria-hidden="true"></div>
    <div class="wiz-nav">
      <button class="ghost sm" id="wizBack">Back</button>
      <button id="wizNext">Next</button>
      <button class="ghost sm" id="wizSkip">Skip tour</button>
    </div>
  </div>
</div>
```

**CSS** — one block after the `#prefs` rules (after line 61), cloning their shape:

```css
#wizard{position:fixed;inset:0;z-index:80;background:var(--felt-edge);overflow-y:auto;
  padding:calc(16px + env(safe-area-inset-top,0px)) 16px
          calc(40px + env(safe-area-inset-bottom,0px))}
#wizard[hidden]{display:none}
```

`z-index:80` sits above `#prefs` (60) and below `#boot` (99): the boot screen fades
out to *reveal* the already-shown wizard (no flash of the table), and opening the
wizard from Preferences covers the prefs overlay. `.wiz-body` mirrors `.prefs-body`
(`max-width:640px;margin:0 auto`). Typography reuses `.lab`, Oswald headings, and
the existing button classes — no new visual language. Step transitions: none beyond
show/hide (which also satisfies R9's reduced-motion requirement for free; any
added fade must sit behind `@media(prefers-reduced-motion:reduce)` like line 45).

## Wizard IIFE — integration points

New IIFE placed after the boot/prefs IIFE (after line 3209). Exact touch points:

| # | Where (anchor) | Change |
|---|---|---|
| 1 | after line 493 (`#prefs` close tag) | insert `#wizard` markup |
| 2 | after line 61 (`.prefsrow` rule) | insert `#wizard` CSS block |
| 3 | before line 3113 (viewmode IIFE) | `WIZ_RETURNING` synchronous snapshot |
| 4 | lines 3143–3148, `hide()` in boot IIFE | after `boot.classList.add('gone')`, call `window.__wizardMaybeShow?.()` (exposed by the wizard IIFE; optional-chained so boot never depends on it) |
| 5 | after line 3209 (boot IIFE end) | the wizard IIFE: state, `show(step)`, nav wiring, `SecureStore.get('craps.wizard.seen')`, `WIZ_RETURNING` check, error backstop |
| 6 | lines 3150–3204 (prefs body build) | add one `.prefsrow` with a "Show the welcome tour" button (`id="wizReplay"`); handler: `$('prefs').hidden=true; window.__wizardShow(0)` |
| 7 | line 3207–3208 (Escape handler) | extend: if `#wizard` is visible, Escape dismisses *it* (marks seen) before falling through to prefs |
| 8 | lines 1396–1449 (`PANEL_GLOSSARY`) | add a `WELCOME TOUR` entry (what it is, that it's skippable, re-run via Preferences → Show the welcome tour) |
| 9 | `coach.py` line 36 (`PANELS`) | mirror the same entry, per the SOP comment at game.html:1396 and coach.py:31–35 |

`show(step)` responsibilities: unhide `#wizard`, reveal section `step`, sync step 2's
cards from `#viewmode.value` and step 3's toggle from the live `[data-d="voice"]`
checkbox, paint dots/nav. `dismiss(reason)` responsibilities: hide, then
`SecureStore.set('craps.wizard.seen','1')` (fire-and-forget with catch).

**Error backstop (R2):** `__wizardMaybeShow` wraps its body in try/catch; the catch
hides `#wizard` and writes the seen flag. A broken wizard costs one tour, never the
game.

**Timing:** boot hides at load+3000ms (backstop 4500ms, lines 3147–3148). The
`SecureStore.get` resolves in microseconds-to-milliseconds; `__wizardMaybeShow` is
`async` and simply awaits it before unhiding — no race with the 3-second boot in
practice, and if storage is slow the wizard appears a beat after the fade, which
is fine.

## What this deliberately does not do

- No direct writes to `craps.view` or `craps.dealer` (R7 keeps one persistence path).
- No focus-trap library; basic focus-to-dialog on show and restore on close.
- No coach-marks over live UI, no interactive practice roll, no localization
  (out of scope; file follow-ups per PROCESS.md).

## Open questions for Eric

1. **Grandfathering** uses `craps.view.v2` as the "existing install" sentinel. On a
   *fresh iOS install restored from an iCloud/device backup*, localStorage may
   survive, so a restored user is treated as returning. Acceptable? (Design says yes.)
2. Should Escape on the *first* step count as "seen forever," or only suppress until
   next launch? Current design: any dismissal is forever (R1/R2 favour never
   re-nagging). Cheap to soften later.
3. Step 4 cost framing says "typically well under a cent per remark" — comfortable
   making that claim in shipped copy, or prefer "a few cents per session at most"?
4. The web build auto-owns Advanced (line 1676). Keep step 4 copy identical on both
   platforms (chosen, simpler and truthful) or hide the purchase sentence on web?
