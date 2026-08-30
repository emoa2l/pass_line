# Shipping Pass Line to the App Store and Google Play

The app is a single HTML file with **no backend**. Capacitor wraps the same source
for both stores.

```bash
npm init -y && npm i @capacitor/core @capacitor/cli @capacitor/preferences
npx cap init "Pass Line" app.passline --web-dir=.
npx cap add ios && npx cap add android
npx cap sync
```

`@capacitor/preferences` is what moves the API key off `localStorage` and into the
iOS Keychain / Android EncryptedSharedPreferences. The code already detects it at
runtime (`SecureStore.native`) and falls back to `localStorage` on the plain web.

## Privacy declarations

Both stores ask what you collect. The honest answer here is **nothing** — you run
no server. What the forms need:

**Apple — App Privacy ("Data Not Collected")**
The developer collects no data. The app sends game state to a third-party AI
provider *chosen by the user, using the user's own API key*, only after explicit
in-app consent. Declare the AI provider as a third-party service in your privacy
policy, not as data you collect.

**Google Play — Data Safety**
- Data collected: **None**
- Data shared: **None by the developer.** Disclose in the policy that the user may
  optionally send gameplay data to an AI provider they configure themselves.
- Encryption in transit: yes (all provider APIs are HTTPS)
- Users can request deletion: yes — "Forget key" erases the credential on-device

You still need a **hosted privacy policy URL** for both stores. The text in the
app's AI setup panel is written to be usable as the basis for it.

## Gambling rules — read before submitting

Both stores restrict real-money gambling. This app is **play money only**:
no real wagering, no cash-out, no purchase of chips. Keep it that way and it is a
game/education title, not a gambling app.

- Apple 1.4.3 / 5.3: simulated gambling is allowed; it must not offer real prizes.
- Google Play: same distinction. Declare it as a game, not "real-money gambling".
- Age rating: both will ask about simulated gambling. Answer **yes** — it rates
  the app 17+ / Mature but is straightforward. Answering no risks removal.

## Bring-your-own-key and IAP

Apple has rejected apps where an external paid service looked like it dodged IAP.
The safe framing, which this app uses: the user brings **their own account with a
third-party AI provider**, the app sells nothing, and the AI features are optional
extras on top of a fully working free app. Do not sell keys or credits in-app.

## Self-contained

Fonts are embedded as data URIs, so the app makes **no network request at all**
until the player uses the coach or dealer. Verified with the browser's own resource
timing: zero external requests at startup. This matters twice — it is what makes the
app genuinely offline, and it keeps the privacy declarations simple (no CDN means no
third-party receives the user's IP just for opening the app).

If you re-add a web font or any CDN asset later, that stops being true and the
privacy answers change.

## Before you submit

- [ ] Replace `icon-192.png` / `icon-512.png` (referenced by the manifest)
- [ ] Host the privacy policy and link it in both store listings
- [ ] Test with AI **off** and the network disabled — the whole app must still work
- [ ] Confirm startup still makes zero external requests (DevTools → Network)
- [ ] Confirm "Forget key" really clears the credential on a device
- [ ] Screenshots that do not imply real-money play
