# First-play wizard — tasks

Branch: `feat/first-play-wizard`. One issue per task on `gitlab.com/emoa2l/passline`
(each with a plain-language *why this matters*, per PROCESS.md). Tasks are ordered;
each ends with a check you can run in a browser. Line anchors are as of the spec
reading (game.html, 3,245 lines) — re-find by the search strings if drifted.

Money-model note: no task below touches bets, payouts, or attribution, so the
`rack + pressed == felt` rules do not apply; the Debug self-test still runs once in
T9 as a regression tripwire.

## T1 — Overlay shell (markup + CSS)

Add the `#wizard` dialog markup after the `#prefs` block (search `prefs-body`,
~line 493) and its CSS after the `.prefsrow` rule (~line 61): `z-index:80`,
safe-area padding cloned from `#prefs` (line 50), `[hidden]{display:none}`,
`.wiz-body` mirroring `.prefs-body`. Five empty `.wiz-step` sections, dots, and
Back/Next/Skip buttons.

**Verify:** in devtools, remove `hidden` from `#wizard`: overlay covers the table,
scrolls, respects the notch in responsive-mode iPhone emulation; re-adding `hidden`
restores the game untouched.

## T2 — Wizard engine + first-launch gate

Add the `WIZ_RETURNING` synchronous snapshot immediately before the viewmode IIFE
(search `craps.view.v2`, ~line 3113). Add the wizard IIFE after the boot IIFE
(~line 3209): `show(step)`, `dismiss()` (writes `craps.wizard.seen='1'` via
`SecureStore`), nav/dots wiring, Skip on steps 1–4, Finish on 5, Escape handling
folded into the existing keydown listener (~3207), try/catch backstop that hides
and marks seen on any error. Hook `window.__wizardMaybeShow?.()` into the boot
`hide()` (~line 3143).

**Verify:** cleared storage → boot fades into step 1; Next/Back walk all five
steps; Skip, Escape, and Finish each dismiss; after any dismissal a reload shows
no wizard. Seed `localStorage['craps.view.v2']='1'` on a cleared profile → no
wizard. Throw inside `show()` temporarily → game unaffected, flag written.

## T3 — Step 1 and step 5 copy

Welcome copy (play-money, no real wagering, tap / long-press-working / roll —
wording consistent with `#hint`, line 591) and Finish copy (Preferences ⚙, re-run
pointer).

**Verify:** read both steps at iPhone SE width — no clipped text, no horizontal
scroll.

## T4 — Step 2: layout choice

Two option cards with CSS-only thumbnails; pre-select from `#viewmode.value` at
show-time; on pick, set the select and dispatch `change` (reuses `apply()`,
~3126). Note the felt view's pass-line-odds behaviour in the copy (~3128).

**Verify:** pick Half table → layout flips live behind the overlay; reload →
felt persists and `#viewmode` reads "Half table"; re-run the tour → felt card is
pre-selected; pick List → reverts. `craps.view` is only ever written by the
existing handler (breakpoint on the wizard confirms no direct write).

## T5 — Step 3: dealer voice

Toggle bound to the live `[data-d="voice"]` checkbox (line 721) via dispatched
`change` (handler at 2501–2516); state read at show-time; copy per design (built
in, free, offline, recorded stickman).

**Verify:** toggle on → sample call plays (local `voice/co11.mp3`, network tab
shows no remote request), Preferences checkbox is checked, `craps.dealer` persists
`voice:true` across reload; toggle left off → `craps.dealer` untouched.

## T6 — Step 4: AI copy (inform, don't sell)

Static copy per the design's content contract: Advanced one-time unlock, own-key
model with OpenRouter default, what an API key is and where it comes from, rough
usage cost, key + consent both required before anything is sent, full game works
without any of it. No buttons besides navigation.

**Verify:** step 4 contains no element wired to `Pro.buy`/`proBuy`; network tab
stays empty across the entire tour (A5). Copy cross-checks against the lockbox
(681–693) and privacy text (2529–2541) — no contradiction.

## T7 — "Show the welcome tour" in Preferences

Add a `.prefsrow` with a replay button into the prefs-body build (~3150–3204);
handler hides `#prefs` and calls `show(0)`. Does not clear the seen flag.

**Verify:** Preferences → Show the welcome tour → step 1; steps 2/3 reflect
current settings; finishing returns to the game; next reload still shows no
automatic wizard.

## T8 — Glossary updates (repo SOP — same change, not a follow-up)

Add a matching `WELCOME TOUR` entry to `PANEL_GLOSSARY` in game.html (SOP comment
at line 1396) **and** `PANELS` in coach.py (line 36): what the tour is, that it is
skippable and shows once, re-run via Preferences → Show the welcome tour.

**Verify:** run `python3 coach.py`, ask the coach "what is the welcome tour?" —
answer comes from the glossary (A8); diff shows both files updated together.

## T9 — Browser test plan (run before the MR)

Execute and record in the MR description:

1. **Fresh first launch** (cleared site data): boot → wizard → full walk-through
   choosing felt + voice on → reload: no wizard, felt view, voice on. (A1, A3, A4)
2. **Skip paths:** clear again; Skip at step 1 → reload, no wizard. Clear; Escape
   at step 3 → reload, no wizard. (A1)
3. **Returning user:** profile with prior state → no wizard ever auto-shows. (A2)
4. **Re-run:** via Preferences, twice in one session. (A6)
5. **No network:** devtools network tab empty for the whole tour except local
   `voice/*.mp3` when voice is toggled on. (A5, R6)
6. **Safe area:** iPhone 15 Pro emulation, portrait + landscape: all controls
   inside the safe area. (A7)
7. **Keyboard + reduced motion:** tab through all wizard controls; with
   `prefers-reduced-motion: reduce` emulated, no animated transitions. (R9)
8. **Regression tripwire:** Debug card → Self-test 200 rolls on 3 seeds — no
   DRIFT lines (wizard must not have perturbed the game path).
9. **Capacitor smoke** (device/simulator, if available before the MR; otherwise
   file the check as its own issue rather than skipping silently): first launch
   shows the tour once; `craps.wizard.seen` lands in native Preferences storage.

## Follow-ups to file, not fold in

- Coach-marks/spotlight variant pointing at the live roll button and a place number.
- Localization of wizard copy.
- Restored-from-backup users are treated as returning (design open question 1) —
  file only if Eric wants different behaviour.
