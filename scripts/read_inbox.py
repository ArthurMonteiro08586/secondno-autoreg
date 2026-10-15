# -*- coding: utf-8 -*-
"""Dump SMS inbox of a reserved number / list account numbers.

Usage:
  python scripts/read_inbox.py <email> <password> --list
  python scripts/read_inbox.py <email> <password> --phone +48XXXXXXXXX --number-id N [--timeout 60]
"""
import json
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secondno import SecondNo  # noqa: E402


def main():
    email, password = sys.argv[1], sys.argv[2]
    sn = SecondNo()
    try:
        sn.login(email, password)
        if "--list" in sys.argv:
            for r in sn.list_numbers():
                print(json.dumps(r, ensure_ascii=False), flush=True)
            return
        phone = sys.argv[sys.argv.index("--phone") + 1]
        number_id = int(sys.argv[sys.argv.index("--number-id") + 1])
        timeout = 60
        if "--timeout" in sys.argv:
            timeout = int(sys.argv[sys.argv.index("--timeout") + 1])
        msgs = sn.read_sms(phone, number_id, timeout=timeout)
        print(json.dumps(msgs, ensure_ascii=False, indent=1), flush=True)
    finally:
        sn.close()


if __name__ == "__main__":
    main()
