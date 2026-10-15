# secondno-autoreg

Full automation for **2nd-no.com** (API host `2no.pl`) — free Polish SMS receiver numbers.

- 3 numbers per account, 3-day reservations (extended on SMS receipt)
- Unlimited accounts (fresh temp-mail or catch-all domain -> Gmail forward)
- Cloudflare Turnstile on reservation, solved via 2captcha or a local free sidecar

Verified live: reserve -> SMS -> OTP extraction (WorkOS, GitLab, New-API panels, forums).

## Protocol notes (reverse-engineered)

All API calls are JSON-RPC: `POST https://2no.pl/` with body `{"id": <int>, "query": {...}}`
and header `x-auth-token` = the `2NR-TOKEN` value from `sessionStorage`.

**Direct HTTP to 2no.pl from outside the browser returns Cloudflare 403** — every call in
this toolkit is executed via `page.evaluate(fetch)` inside the logged-in browser context.

| id | purpose | notes |
|----|---------|-------|
| 310 | random free number | response carries `captcha:"turnstile"` when 301 needs a token |
| 301 | reserve number | `query={number_id, name, color, right_to_transfer_number, response_key=<turnstile token>}` |
| 311 | my numbers | `{offset, limit}` -> `result[]` with `number`, `number_id`, `reservation_to` |
| 415 | getMessagesForNumber_v2 | `phone`=**string** (`+48...`), `number_id`=**int**; real messages arrive under `badges.messages[]`, `data.messages` stays empty |

Turnstile sitekey (public, from site bundle): `0x4AAAAAAAh6YYTPTzEcN3Ep`

## Install

```bash
pip install -r requirements.txt
python -m playwright install chromium   # or use installed Chrome (channel="chrome")
```

Captcha config (pick one):
- env `TWOCAPTCHA_API_KEY=<key>` — paid, reliable (~$0.0014/solve)
- `data/captcha_keys.json` — `{"keys": [{"key": "...", "label": "..."}]}`; the richest key with balance >$0.05 is auto-selected
- local sidecar on `http://127.0.0.1:8877` (free) — auto-preferred when alive; override with env `SIDECAR_URL`

Email backend for fresh accounts (optional):
- default: tempmail.lol (built-in, zero config)
- `--gmail`: catch-all domain -> ForwardEmail -> Gmail; needs env `GMAIL_ADDR`, `GMAIL_APP_PW`, `MAIL_DOMAIN`

## Usage

Register N fresh accounts + first number (appends to `data/state.json`):

```bash
python scripts/register_account.py 3
python scripts/register_account.py 3 --gmail
```

Reserve a number on an existing account and wait for an OTP (bridge for other autoreg flows):

```bash
python scripts/reserve_read.py <email> <password> reserve.json code.json 300 2026-10-15T10:00:00
# reserve.json appears ASAP -> paste the phone into the target service
# code.json gets {"code": "123456", "text": "...", "ts": "..."} when the SMS lands
```

Dump inbox / list numbers:

```bash
python scripts/read_inbox.py <email> <password> --list
python scripts/read_inbox.py <email> <password> --phone +48XXXXXXXXX --number-id N --timeout 60
```

Python API:

```python
from secondno import SecondNo, get_solver

sn = SecondNo(solver=get_solver())
sn.login(email, password)
info = sn.reuse_active(set()) or sn.get_number()   # REUSE-FIRST
code, text = sn.wait_otp(info["full"], info["number_id"], timeout=300)
sn.close()
```

## Hard-won pitfalls

1. **React hydration (site change 2026-10-12).** Filling the login form instantly after
   `domcontentloaded` hits un-hydrated inputs (`inputs missing` / setter `TypeError`).
   `SecondNo.login` waits for `input[type=password]`, uses guarded native-setter fills
   and retries once. Do not "simplify" it back.
2. **REUSE-FIRST.** The 3-number cap means most reservations should reuse an active
   unused number from id 311 — that skips the turnstile solve entirely. Mark a number
   used (`used_numbers.json`) **only after a real OTP**; a dry test run must not burn it.
   Hitting 301 when the cap is reached returns HTTP 400.
3. **min_ts filter.** Without it you will feed the target service a stale code from the
   previous run. Pass an ISO timestamp taken right before you trigger the SMS.
4. **2captcha API.** Submit only via `in.php` (`res.php` -> `ERROR_EMPTY_METHOD`);
   balance check is `POST res.php {action:getbalance}` and the balance value lives in
   the `request` field. YesCaptcha works too but the task type must be
   `TurnstileTaskProxyless` (not `AntiTurnstile`).
5. **tempmail.lol v2.** The inbox token goes in the query string (`?token=`), not a
   Bearer header. Yield ~50%; if delivery stalls, switch to the Gmail-forward backend.
6. **These numbers are NOT for Telegram or OpenAI.** Telegram bans the whole free pool
   (`PhoneNumberBannedError` on send_code) and OpenAI never delivers to it. Good targets:
   WorkOS, GitLab 2FA-ish flows, New-API panels, forums, generic web OTP.
7. **Fingerprint anti-fraud.** The vendor flags repeat signups from one IP — for account
   farming rotate proxies per registration; reservation/SMS reading is fine from one IP.

## Repo layout

```
secondno/client.py    browser JSON-RPC client (SecondNo), mail inboxes, full_cycle
secondno/captcha.py   2captcha + free sidecar turnstile solvers
scripts/register_account.py   fresh accounts + first number
scripts/reserve_read.py       REUSE-FIRST reserve + OTP poll (CLI bridge)
scripts/read_inbox.py         number list / SMS dump
data/                         state.json, captcha_keys.json, used_numbers.json (gitignored)
```
