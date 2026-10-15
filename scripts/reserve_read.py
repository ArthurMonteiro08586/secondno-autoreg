# -*- coding: utf-8 -*-
"""Reserve a number on an EXISTING account (REUSE-FIRST) and poll for an OTP code.

Usage: python scripts/reserve_read.py <email> <password> <reserve_file> <code_file> [poll_timeout] [min_ts]

Writes {"phone", "number_id", "expires"} to reserve_file ASAP (so the caller can
paste the number into the target service), then polls SMS and writes
{"code", "text", "ts"} to code_file (or {"code": null, "err": ...} on failure).

REUSE-FIRST: active unused reservations are reused before spending a turnstile
solve on a fresh one (3-number cap per account). used_numbers.json (next to
reserve_file) tracks numbers that already delivered an OTP — mark used ONLY
after a real code, a dry test run must not burn the number.
min_ts: ignore SMS older than this timestamp (ISO prefix compare) — avoids
feeding a stale code from a previous run.
"""
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secondno import SecondNo, get_solver  # noqa: E402


def main():
    email, password, reserve_file, code_file = sys.argv[1:5]
    poll_timeout = int(sys.argv[5]) if len(sys.argv) > 5 else 300
    min_ts = sys.argv[6] if len(sys.argv) > 6 else None

    try:
        solver = get_solver()
    except Exception as e:
        print("solver init err:", e, flush=True)
        solver = None
    sn = SecondNo(solver=solver)
    try:
        sn.login(email, password)
        used_file = os.path.join(os.path.dirname(os.path.abspath(reserve_file)), "used_numbers.json")
        used = set()
        try:
            used = set(json.load(open(used_file, encoding="utf-8")))
        except Exception:
            pass
        info = None
        try:
            info = sn.reuse_active(used)
            if info:
                print("REUSE active number", info["full"], info["number_id"], flush=True)
        except Exception as e:
            print("reuse scan err:", str(e)[:100], flush=True)
        if not info:
            try:
                info = sn.get_number()
            except Exception as e:
                print("reserve fresh failed:", str(e)[:150], flush=True)
        if not info:
            raise RuntimeError("no free/reservable number (limit reached, all used)")
        phone, number_id = info["full"], info["number_id"]
        with open(reserve_file, "w", encoding="utf-8") as f:
            json.dump({"phone": phone, "number_id": number_id,
                       "expires": info.get("expires")}, f)
        print("RESERVED", phone, number_id, flush=True)

        deadline = time.time() + poll_timeout
        while time.time() < deadline:
            try:
                msgs = sn.read_sms(phone, number_id, timeout=16, poll=8)
                cands = []
                for m in msgs:
                    text = str(m.get("text") or m.get("body") or "")
                    ts = str(m.get("created_at") or m.get("date") or m.get("time") or "")
                    if min_ts and ts and ts < min_ts:
                        continue
                    mm = re.search(r"\b(\d{4,8})\b", text)
                    if mm:
                        cands.append((ts, mm.group(1), text))
                if cands:
                    cands.sort()
                    ts, code, text = cands[-1]
                    with open(code_file, "w", encoding="utf-8") as f:
                        json.dump({"code": code, "text": text[:250], "ts": ts}, f,
                                  ensure_ascii=False)
                    digits = re.sub(r"\D", "", str(phone))
                    used.add(digits[2:] if digits.startswith("48") else digits)
                    try:
                        json.dump(sorted(used), open(used_file, "w", encoding="utf-8"))
                    except Exception:
                        pass
                    print("CODE", code, flush=True)
                    return
            except Exception as e:
                print("poll err:", str(e)[:120], flush=True)
            time.sleep(6)
        with open(code_file, "w", encoding="utf-8") as f:
            json.dump({"code": None, "err": "timeout"}, f)
        print("TIMEOUT", flush=True)
    except Exception as e:
        with open(code_file, "w", encoding="utf-8") as f:
            json.dump({"code": None, "err": str(e)[:200]}, f)
        print("FATAL", str(e)[:200], flush=True)
        sys.exit(2)
    finally:
        sn.close()


if __name__ == "__main__":
    main()
