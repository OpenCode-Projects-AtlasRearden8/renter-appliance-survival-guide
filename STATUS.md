# STATUS.md — Renter Appliance Survival Guide

**Last updated:** 2026-11-05 · **Commit:** `Initial build: Renter Appliance Survival Guide docs, static site builder, and tests`

## What was built

A local-first, beginner-friendly appliance manual ("what a friend would explain") covering **dishwasher, washer, dryer, refrigerator, and HVAC basics** — plus printable take-along sheets — for the Asdale Dynamics plain-English library. Complements *home-repair-with-ai-guide* and *home-maintenance-mcp-server*.

### Content (docs/, 14 Markdown files, ~610 lines & growing)

- **index.md** — friendly landing page & one-paragraph summary of the whole guide
- **how-to-use.md** — the "decode, don't despair" method, symbols (STOP / FREE / CHEAP / PRO), the renter twist, safety basics
- **dishwasher.md · washer.md · dryer.md · fridge.md · hvac.md** — each covers:
  - what error codes *honestly* mean (code-family tables: what codes say vs. what's usually actually wrong)
  - the monthly cleaning list (dishwasher filter & spray arms, washer gasket & pump filter, dryer lint screen/vent/flap, fridge coils & gaskets & drain, HVAC filter & condensate line & outdoor unit)
  - when to call a pro (with hard STOP lines: gas smell, burning smells, water-near-power, refrigerant, repeated breaker trips)
  - reset basics tailored per appliance
- **reset-basics.md** — the reset ladder (button → control lock → 60-second power cycle → …), when resets are the *wrong* move, firmware/smart-appliance honesty
- **replace-vs-keep.md** — energy-hog math in plain dollars, per-appliance lifespan/replace-signal cheat sheet, decision flowchart, renter reality check
- **error-code-log-sheet.md** — printable log table + reminder card
- **call-a-pro-checklist.md** — pre-call prep, questions to ask, red flags, the renter escalation sequence, emergency-numbers table (blank for local entries)
- **glossary.md** — friend-translation definitions of the words manuals use

### Code

- **build.py** — dependency-light static-site builder (stdlib + `markdown`): renders all docs into `site/*.html` with shared nav/CSS template, rewrites internal links, converts task lists to checkboxes, validates nav ↔ docs wiring with clear error messages
- **tests/test_build.py** — 21-test `unittest` suite (source completeness, unique titles, link resolution, markdown conversion, page templating, end-to-end build into temp dir)
- **README.md, LICENSE (MIT), .gitignore** — repo hygiene; `site/` is build output (regenerated, not committed)
- Git initialized; single clean commit; author = existing git identity; no remote, no push

## How to run it

```bash
python3 -m pip install markdown       # only third-party dependency
python3 -m unittest discover -s tests # run the test suite
python3 build.py                      # build the site into ./site
python3 build.py --open               # build + print the index.html file path
                                      # then open site/index.html in a browser
```

## Verification results

- `python3 -m py_compile build.py` — OK
- `python3 build.py` — **OK: built 12 pages into site/** (all 12 nav pages + style.css)
- `python3 -m unittest discover -s tests` — **OK: 21 tests passed**
- Cross-link audit: every `.md` link inside docs/ resolves to an existing doc (test-enforced; no internal 404s in output)
- Secrets scan (`API key`/`secret`/`password`/`sk-…` patterns): clean — no secrets or personal data in any file
- Non-ASCII audit: no stray CJK/Cyrillic characters (test-enforced after fixing a few editing slips)
- Rendered-page spot checks: tables, blockquotes, checkbox inputs, escaping (`&amp;`), nav `current` page marker all correct

## Known gaps / honest limitations

- **Error-code tables are code *families*, not exhaustive per-brand decoder rings.** Brand-specific codes (Bosch `E24`, Whirlpool `F5 E3`, LG `OE`, etc.) vary by model year; the guide teaches the honest pattern and points to owner's manuals for exact strings.
- **No CLI `--open` that actually launches a browser** — it prints the `file://` path instead (deliberately quiet/local-first; avoids surprising GUI behavior).
- **The printable sheets are HTML tables, not PDFs** — fine for browser printing; a dedicated print stylesheet is a possible upgrade.
- **Fridge/HVAC chapters lean on lifelong-uptime rules of thumb** (lifespans, SEER-era savings) — averages, not engineering specs.
- **No search, no dark mode, no syntax highlighting** on the built site — fine for a guide this size; could add if it grows.
- **Companion projects** (*home-repair-with-ai-guide*, *home-maintenance-mcp-server*) are referenced by name but not cross-embedded.
- Tests require the `markdown` package to be installed (documented in README); a graceful install-hint error is shown otherwise.
