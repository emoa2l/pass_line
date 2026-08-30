#!/usr/bin/env bash
# Creates the M0 milestone, labels and issues on gitlab.com/emoa2l/passline.
#
#   export GITLAB_TOKEN=glpat-...        # needs 'api' scope
#   ./scripts_create_issues.sh
#
set -euo pipefail
P="emoa2l%2Fpassline"
API="https://gitlab.com/api/v4"
H=(--header "PRIVATE-TOKEN: ${GITLAB_TOKEN:?export GITLAB_TOKEN first}")

say(){ printf '%s\n' "$*"; }

say "Creating milestone…"
MID=$(curl -s "${H[@]}" -X POST "$API/projects/$P/milestones" \
  --data-urlencode "title=M0 — First release" \
  --data-urlencode "description=Ship Pass Line to the App Store and Google Play. Free craps table, one-time Advanced unlock for the AI coach and dealer." \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("id",""))')
say "  milestone id: ${MID:-(already exists)}"

mklabel(){ curl -s -o /dev/null "${H[@]}" -X POST "$API/projects/$P/labels" \
  --data-urlencode "name=$1" --data-urlencode "color=$2" --data-urlencode "description=$3" || true; }
say "Creating labels…"
mklabel blocker   "#B60205" "Blocks the M0 release"
mklabel store     "#0E8A16" "App Store / Play Store submission"
mklabel packaging "#1D76DB" "Capacitor / native build"
mklabel legal     "#5319E7" "Privacy, terms, compliance"
mklabel design    "#D93F0B" "Icons, screenshots, store art"
mklabel qa        "#FBCA04" "Testing and verification"
mklabel cleanup   "#C5DEF5" "Tidy-up, not release blocking"

mkissue(){ # title, labels, body
  local id
  id=$(curl -s "${H[@]}" -X POST "$API/projects/$P/issues" \
    --data-urlencode "title=$1" \
    --data-urlencode "labels=$2" \
    --data-urlencode "description=$3" \
    ${MID:+--data-urlencode "milestone_id=$MID"} \
    | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("iid","ERR"))')
  say "  #$id  $1"
}

say "Creating issues…"

mkissue "Set up the Capacitor project for iOS and Android" "blocker,packaging" \
'The repo is currently a bare web app: there is no `package.json`, no `capacitor.config`, and no `ios/` or `android/` directory. Nothing can be submitted until that exists.

```bash
npm init -y
npm i @capacitor/core @capacitor/cli @capacitor/preferences
npx cap init "Pass Line" app.passline --web-dir=.
npx cap add ios && npx cap add android
npx cap sync
```

**Why this matters:** `@capacitor/preferences` is what moves the API key out of `localStorage` and into the iOS Keychain / Android EncryptedSharedPreferences. `SecureStore` in `game.html` already detects the plugin at call time and falls back to `localStorage` when it is absent — so without this step the key silently stays in web storage, which is not acceptable for a credential.

**Done when:** both platforms build and launch, and `SecureStore.native` reports true on a device.'

mkissue "Wire the purchases plugin and the advanced entitlement" "blocker,packaging" \
'`Pro` in `game.html` expects `window.Capacitor.Plugins.Purchases` with an entitlement named **`advanced`**. Nothing is wired yet, so on a real device `Pro.load()` finds no plugin and treats the build as unlocked.

RevenueCat’s Capacitor plugin is the least work and handles both stores.

**Already handled in code — do not re-implement:**
- Restore Purchase button exists (Apple requires it).
- A paid unlock is never revoked by a failed or stale store check: only a successful entitlement grants it, and nothing automatic takes it away. Verified against an empty response and an offline store.

**Done when:** a sandbox purchase unlocks the AI panel, and it survives an app restart with the device offline.'

mkissue "Create the passline.advanced product in both stores" "blocker,store" \
'One-time **non-consumable** purchase, product id `passline.advanced`.

- App Store Connect: create the IAP, submit for review with the build.
- Play Console: create the managed product with the same id.
- Price: $4.99 (decided).

**Note:** store product setup usually takes longer than the code, and the IAP is reviewed alongside the first build. Starting this early avoids it becoming the critical path.

**Done when:** the product is live in both consoles and returns from `getOfferings()` in a sandbox build.'

mkissue "App icons — the manifest points at files that do not exist" "blocker,design" \
'`manifest.webmanifest` references `icon-192.png` and `icon-512.png`. Neither file is in the repo, so the PWA install and both native builds have no icon.

Needed:
- `icon-192.png`, `icon-512.png` (maskable-safe, keep the subject inside the middle 80%)
- iOS app icon set (1024×1024 source)
- Android adaptive icon (foreground + background layers)

The table’s own palette is a reasonable starting point: felt green `#0B5D3B`, brass `#C9A227`, bone `#F2EDE3`.'

mkissue "Host a privacy policy and link it in both listings" "blocker,legal" \
'Both stores require a reachable privacy-policy URL before submission.

The disclosure text already in the app’s AI setup panel is written to serve as the basis — it covers what leaves the device, what never does, who receives it, how to turn it off, and the children/no-real-money position.

Points it must keep making:
- The developer operates no server and receives no user data.
- Gameplay state goes only to the AI provider the user configures, with their own key, after explicit consent.
- The key is stored in the OS keystore and is sent to that provider alone.
- No analytics, no tracking, no device identifiers.

**Done when:** the URL is live and entered in App Store Connect and Play Console.'

mkissue "Store listings: screenshots, description, age rating" "blocker,store" \
'For both stores:

- Screenshots at the required device sizes. **Do not imply real-money play.**
- Description that leads with what is free (the whole table and all tracking) and is explicit that Advanced is a one-time unlock for the AI features.
- **Age rating: answer YES to the simulated-gambling question.** It rates the app 17+/Mature. Answering no risks removal later, which is far worse than the rating.
- Apple App Privacy: **Data Not Collected**.
- Google Play Data Safety: **no data collected, none shared by the developer**; disclose the optional user-configured AI provider in the policy.

See `STORES.md` for the reasoning behind each answer.'

mkissue "Device QA before submission" "blocker,qa" \
'Run on real hardware, not just the simulator:

- [ ] Purchase flow completes in sandbox on iOS and Android
- [ ] Restore Purchase works on a second device with the same account
- [ ] The unlock survives an app restart **with the device offline**
- [ ] The API key lands in the Keychain / EncryptedSharedPreferences, not `localStorage`
- [ ] “Forget key” genuinely erases the credential
- [ ] With AI off and the network disabled, the whole table still works
- [ ] Startup makes zero external requests (fonts are inlined — verify it stays that way)
- [ ] The Debug card’s self-test reports clean across several seeds
- [ ] Rotation and small-screen layout hold up

The in-app Debug card records a seeded trace, so any failure found here can be replayed exactly rather than described.'

mkissue "Decide repository visibility before launch" "cleanup" \
'`github.com/emoa2l/pass_line` is currently **public**, and this GitLab project mirrors the same source.

The app is a paid product whose entire logic is client-side, so a public repo means anyone can clone and build it without paying. That may be a deliberate choice (open source, trust, contributions) — it just should not happen by accident.

**Decide:** keep public, or make both private before launch.'

mkissue "Remove development-only files from the shipped bundle" "cleanup" \
'`coach.py` and `serve.py` are development conveniences and should not ship inside the app package.

- `coach.py` — the old local AI proxy; the app now calls providers directly.
- `serve.py` — local static server for testing.

The in-app **Local proxy (coach.py)** provider is already hidden outside localhost, so users never see it. This is about keeping them out of the Capacitor `webDir` copy.

Keep both in the repo for development; exclude them from the bundle.'

say ""
say "Done. https://gitlab.com/emoa2l/passline/-/issues"
