# -*- coding: utf-8 -*-
"""Register fresh 2nd-no.com account(s) + reserve first number.

Usage: python scripts/register_account.py [N] [--gmail]
  default inbox: tempmail.lol (built-in, no config)
  --gmail: catch-all domain -> ForwardEmail -> Gmail (needs GMAIL_ADDR, GMAIL_APP_PW, MAIL_DOMAIN env)

Accounts + numbers are appended to data/state.json.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secondno import full_cycle, GmailForwardInbox  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 1
    inbox_factory = GmailForwardInbox if "--gmail" in sys.argv else None
    results = full_cycle(n, inbox_factory=inbox_factory)
    ok = 0
    for r in results:
        print(json.dumps(r, ensure_ascii=False), flush=True)
        if not r.get("error"):
            ok += 1
    print(f"DONE {ok}/{n} accounts registered", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
