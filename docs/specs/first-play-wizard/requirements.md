# First-play wizard — requirements

Stage: **spec** (per `docs/PROCESS.md`; triage/scope folded in — this document states the
problem and the boundary as well as the behaviour).

## Why this matters

A brand-new player opens Pass Line and lands on a full craps layout with no explanation of
what the app is (play-money practice, not gambling), how to bet, why there are two table
views, that a free recorded stickman voice exists, or what the AI features are and are not.
The AI story in particular needs telling carefully: coach + verbal dealer are part of a
one-time Advanced purchase, they run on the *player's own* provider key, and nothing is
ever sent anywhere without a key **and** explicit consent. Today all of that is spread
across the AI-setup card, the privacy details, and tooltips a new player will never open.
One skippable tour at first launch fixes the first-session experience without touching the
game for anyone who already plays.

## The feature

A first-launch setup wizard ("welcome tour") that appears once, after the boot screen
fades, for players with no prior state. Five steps, in order; every step can be dismissed;
the whole tour can be skipped from any step. Re-runnable later from Preferences.

### Steps

1. **Welcome / what this is.** Play-money craps practice — no real wagering, no chips for
   sale. The one-minute basics: tap a bet area to bet, long-press a place number to toggle
   working/off (same wording family as the existing `#hint`, game.html:591), press Roll.
2. **Layout choice.** List view vs Half-table (felt) view, with a short description (and a
   lightweight visual cue) of each. The player's pick is written through the *existing*
   `#viewmode` control so the current persistence (`craps.view`) and `apply()` path are
   reused, not duplicated.
3. **Dealer voice.** Explain the recorded stickman: built in, free, works offline, calls
   the rolls. One switch that sets the existing `DealerCfg.d.voice` pref through the
   existing `[data-d="voice"]` checkbox path (so the same save/flash/sample-clip behaviour
   fires). Default stays off if the player does nothing.
4. **AI features — inform, don't sell.** States plainly: the AI coach and verbal dealer
   are part of the one-time Advanced purchase; they run on the player's own AI provider
   key (OpenRouter is the default provider); what an API key is, where one comes from
   (the provider's website), and that usage is billed by the provider, typically cents
   per session; nothing is sent anywhere until a key is added **and** the consent
   disclosure is accepted in AI setup; the whole game works fully without any of it.
   **No purchase button, no price display, no "unlock now" call to action in the wizard.**
5. **Finish.** Everything shown here lives in Preferences (the ⚙ button); the tour can be
   re-run any time via a new "Show the welcome tour" control in Preferences.

## Requirements

- **R1 — shows once.** First launch is detected via the existing storage helpers
  (`SecureStore`, game.html:1522, which is Capacitor Preferences on device and
  localStorage on the web). A completed-or-skipped flag persists; the wizard never
  appears again unless explicitly re-run.
- **R2 — never blocks a returning user.** Players with pre-existing state (anyone who has
  loaded the app before this feature ships) are grandfathered: they do not see the wizard.
  Every step has a visible skip/close affordance; Escape closes it; any dismissal marks it
  seen. A JS error inside the wizard must fail toward *hidden and marked seen*, never
  toward a stuck overlay.
- **R3 — single-file.** All wizard HTML/CSS/JS lives inside `game.html`, following the
  existing `#prefs` overlay pattern. No new files, no build step, no external assets
  beyond the already-shipped `voice/*.mp3` (played only if the player turns the voice on).
- **R4 — identical on Capacitor iOS and plain browser.** No Capacitor-only APIs on the
  wizard path except through `SecureStore`, which already abstracts the difference. Copy
  in step 4 must remain truthful on the web build, where `Pro.owned` is simply true
  (game.html:1676) and there is no store: the purchase is described as how the *app
  stores* gate the feature, not pitched.
- **R5 — safe-area aware.** The overlay uses `env(safe-area-inset-*)` padding exactly as
  `#prefs` does (game.html:50).
- **R6 — no network calls.** The wizard itself performs zero fetches. Turning the voice
  on plays a bundled local clip (existing behaviour of the voice toggle); choosing a
  layout writes localStorage. Step 4 is text only — it must not test keys, ping
  providers, or contact the store.
- **R7 — settings write through existing controls.** Layout → the `#viewmode` select
  (game.html:577, wiring at 3113–3136). Voice → the `[data-d="voice"]` checkbox
  (game.html:721, wiring at 2501–2516). The wizard never writes `craps.view` or
  `craps.dealer` directly.
- **R8 — re-run control.** A "Show the welcome tour" row is added to the Preferences body
  (`#prefsBody`, populated at game.html:3150–3204). Re-running shows the same wizard;
  steps 2 and 3 reflect the player's *current* settings when re-run.
- **R9 — accessibility.** `role="dialog"`, labelled; reduced-motion users get no
  animated transitions (match the existing `prefers-reduced-motion` guards, e.g.
  game.html:45); all controls reachable by keyboard in the browser build.
- **R10 — glossary SOP.** `PANEL_GLOSSARY` in game.html (line 1396, SOP comment at that
  line) and `PANELS` in coach.py (line 36) gain a matching entry describing the welcome
  tour and where to re-run it, in the same change.

## Out of scope

- Any change to betting, payouts, or money tracking (the money-model invariant is
  untouched; no `rack + pressed == felt` exposure).
- Interactive "try it now" practice rolls inside the wizard.
- Purchasing flow changes, RevenueCat work, consent-flow changes.
- Coach-marks / spotlight highlighting of live UI elements (a follow-up if wanted —
  file it, don't fold it in).
- Localization.

## Acceptance criteria (verify by running in the browser, per PROCESS.md)

- **A1.** With cleared storage, load `game.html`: boot screen shows, fades, wizard step 1
  appears. Reload: wizard does *not* appear again after any dismissal (skip at step 1,
  Escape at step 3, and Finish at step 5 each tested).
- **A2.** With storage populated as an existing player (`craps.view.v2` present) but no
  wizard flag, the wizard does not appear.
- **A3.** Choosing Half-table in step 2 flips the live layout behind the overlay, and
  `#viewmode` shows "Half table" afterwards; the choice survives reload. Same for List.
- **A4.** Turning voice on in step 3 checks the `[data-d="voice"]` box in Preferences,
  plays the sample call, and survives reload (`craps.dealer` has `voice:true`). Leaving
  it off leaves `craps.dealer` untouched.
- **A5.** Step 4 renders no button that starts a purchase and triggers zero network
  requests (verify in the network tab across the full tour).
- **A6.** Preferences shows "Show the welcome tour"; activating it opens the wizard at
  step 1; completing it returns to the game with settings intact.
- **A7.** On an iPhone-sized viewport with notch emulation, no wizard control sits under
  the notch or home indicator.
- **A8.** The coach, asked "what is the welcome tour?" via the local `coach.py` path,
  answers from the updated glossary.
