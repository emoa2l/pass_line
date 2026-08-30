# How work happens here

Adapted from the Ksymmetry spec-pipeline. Same stages, this project's tracker.

## Stages

| Stage | Artifact | Done when |
|---|---|---|
| **triage** | `docs/specs/<slug>-triage.md` | The problem is stated, and it is clear whether it is worth doing |
| **scope** | `docs/specs/<slug>-scope.md` | Boundaries agreed: what is in, what is explicitly out |
| **spec** | `docs/specs/<slug>.md` | Behaviour and test criteria written down before code |
| **implement** | commits on a branch | Criteria pass, verified by running it |
| **validate** | MR + evidence | Reviewed against the criteria, not against intent |

## Rules

- **One issue per unit of work**, on `gitlab.com/emoa2l/passline`. Every issue carries a
  plain-language *why this matters* — a ticket nobody can motivate is a ticket nobody
  should work.
- **Test criteria check what a change does, not what it claims.** Verify by running it
  in the browser, not by reading the diff.
- **The money model is load-bearing.** Any change touching bets, payouts or attribution
  must keep `rack + pressed == felt` true every roll, and must be checked with the
  Debug card's seeded self-test across several seeds before it lands.
- **Findings discovered mid-work get filed, not fixed inline.** A change stays the size
  it was scoped to be.
- **A branch lands via MR**, never by pushing to `main` directly once there is a second
  contributor.

## Branch names

`feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`.
