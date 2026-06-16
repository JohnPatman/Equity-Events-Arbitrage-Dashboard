# CA / Equity-Events Dashboard — Fix Pack (June 2026)

All paths below are **relative to the repo root**. The folder layout in this
download mirrors the repo, so you can copy each file into the same location.
Keep filenames exactly as-is (including the spaces in page 6).

## What was broken & what changed

### 1. yfinance MultiIndex crash (root cause of several "stopped working" tools)
yfinance now returns **MultiIndex columns even for a single ticker**, so the old
`float(data["Close"].iloc[-1])` raised `TypeError`. Your newest page (the SPY
sim) already guarded against this; the older code didn't.
- `pages/1_Scrip_Arbitrage.py` — flatten + scalar-coerce helper, `auto_adjust=False`,
  try/except so a fetch failure falls back to the manual override instead of crashing.
  Also cached the price fetch (15-min TTL).
- `scripts/arbitrage/lmp_scrip_arbitrage.py` — same flatten fix in `get_lmp_price_pence`.
- `modules/arbitrage/adr_arbitrage.py` — robust `_last_close` (5-day window + retries),
  so empty/rate-limited `.history()` no longer throws `IndexError`; one failing pair
  no longer kills the page.

### 2. Earnings Intelligence — "not gathering latest data"
Not a code bug: the static `Data/earnings/*.csv` only ran to **Feb 2026**, so every
"Next Earnings Date" is now in the past → N/A everywhere.
- `modules/earnings/earnings.py` — added live single-ticker refresh
  (`fetch_earnings_live` via `get_earnings_dates`), a `merge_earnings` that prefers
  live rows on date collisions, `compute_stats`, and an `is_stale` check. Kept the old
  `load_earnings()` signature for backward-compat.
- `pages/5_Earnings_Intelligence.py` — loads stored data, and if it's stale (or you hit
  **Refresh live**) pulls just that one ticker live (6-hour cache) and merges. Shows a
  data-source / freshness badge. Single-ticker live calls rarely get rate-limited.
- `scripts/fetch_earnings.py` — hardened (supported `get_earnings_dates`, retries,
  polite sleep, never overwrites a good CSV with an empty result) for when you want to
  refresh the whole stored base.

### 3. Upcoming UK Dividends — "isn't finding data"
Two problems: the stored CSVs were stale (most pay dates in 2025, now filtered out as
past), and the scrapers were unfixable in production — `fetch_hsbc_dividends.py` uses
**Selenium/ChromeDriver** (won't run on Streamlit Cloud) and literally regex-matches
hardcoded strings like `"18 Dec 2025"`; AZN produced an empty file.
- `modules/dividends/uk_dividends.py` (NEW) — self-updating calendar from yfinance:
  last declared dividend + ex-date from `.get_dividends()`, forward dates from
  `.calendar` when published, an **indicative** next ex-date projected from payment
  cadence (clearly flagged) otherwise, and a static-CSV fallback if Yahoo is down.
- `modules/dividends/__init__.py` (NEW) — package marker.
- `pages/6_Upcoming Popular UK Dividends.py` — rewritten to use the module, with a
  refresh button, a "Basis" column showing where each date came from, and an honest
  currency caveat (UK listings in pence; HSBC in USD).

### 4. Security — committed FRED API key
`modules/macro/load_macro.py` had a hardcoded key in a public repo.
- Now reads from `st.secrets["FRED_API_KEY"]` → env var → keyless, and added
  `raise_for_status` + graceful empty-frame handling.
- **ACTION REQUIRED (do this yourself):** rotate the old key at
  https://fredaccount.stlouisfed.org/apikeys (treat the committed one as burned), then
  add the new one in Streamlit Cloud → App → Settings → Secrets as:
  `FRED_API_KEY = "..."`. Locally, copy `.streamlit/secrets.toml.example` to
  `.streamlit/secrets.toml` (gitignored).

### 5. FX hardening
`modules/arbitrage/fx.py` — `raise_for_status`, tries `frankfurter.dev` then `.app`,
raises only if all sources fail.

### 6. Housekeeping
- `.gitignore` (NEW) — keeps `secrets.toml` and `__pycache__` out of git.
- `.streamlit/secrets.toml.example` (NEW) — secrets template.
- Still worth doing manually: delete the stray `Create requirements.txt` file; the
  spaces in `2_Dividend_Growth Model.py` and `6_Upcoming Popular UK Dividends.py`
  filenames are harmless but untidy.

## What I could NOT verify here
This sandbox can't reach Yahoo/FRED/Frankfurter/HL, so the live data paths are written
against the confirmed yfinance 0.2.66 API but not run end-to-end. The offline logic
(MultiIndex flattening, earnings merge/stats/staleness, dividend fallback parsing) is
tested and passing. The HL scraper is more resilient but HL renders tables client-side,
so if Country Exposure still comes back empty for a fund, that table needs a non-HTML
source (HL fund API or a stored CSV) — tell me and I'll wire that up.

## Deploy
1. Copy each file into its matching repo path (preserve names).
2. Rotate the FRED key and set it in Streamlit secrets.
3. `git add -A` → `git commit -m "Fix yfinance MultiIndex, live earnings + UK dividends, secrets"` → `git push`
4. Streamlit Cloud redeploys automatically.
