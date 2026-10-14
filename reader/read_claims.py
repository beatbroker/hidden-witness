#!/usr/bin/env python3
"""THE HIDDEN WITNESS: the shielded claim reader.

Reads the game wallet with its viewing key (it can see, never spend), finds
claims sent as shielded Zcash payments, and checks each one.

DROPS: at odd hours a code drops on X, marked with ⌖. Each code lives for a
fixed window (60 minutes). A player catches the drop by sealing the code in a
shielded payment that is mined inside the window. The clock is the chain: the
block's own timestamp decides, plus a few minutes' grace for mining.
Identity is the player's own shielded address (the memo's reply field); the
public board only ever sees a keyed hash of it.

Public results: drop, seat, block, txid, caught or not. The code, the sender,
the amount, the address and the memo never leave this script.

Environment:
  HW_UFVK              the game wallet's unified full viewing key (uview1...)
  HW_BIRTHDAY          block height the game wallet was created at
  HW_DROPS             JSON list, kept secret: [{"id": "d1", "code": "ASH 41",
                       "opens": "2026-10-16T03:17:00-07:00", "minutes": 60}, ...]
  HW_GRACE_MINUTES     extra minutes after a window for mining (default 5)
  HW_ANSWERS           (optional, legacy riddle rounds) JSON: {"round": "answer"}
  SUPABASE_URL         https://<project>.supabase.co
  SUPABASE_SERVICE_KEY service role key (kept secret; never in the page)
  DEVTOOL              path to the zcash-devtool binary
  WALLET_DIR           where the view-only wallet database lives
  HW_LWD               lightwalletd servers (default: zecrocks)
  HW_DRY_RUN=1         print results instead of writing them
"""

import datetime
import hashlib
import hmac
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request

DEVTOOL = os.environ.get("DEVTOOL", "zcash-devtool")
WALLET_DIR = os.environ.get("WALLET_DIR", "./hw_wallet")
LWD = os.environ.get("HW_LWD", "zecrocks")
DRY = os.environ.get("HW_DRY_RUN") == "1"

# The memo the page writes (one line; line breaks or "|" both work, order doesn't matter):
#   THE HIDDEN WITNESS | seat: 214 | code: ASH 41 | reply: u1...
# "reply" is the player's own shielded address: their identity in the game, and where prizes go.
MEMO_TAG = "THE HIDDEN WITNESS"
UA_RE = re.compile(r"^(u1|zs1)[0-9a-z]{20,}$")


def run(*args):
    cmd = [DEVTOOL, "wallet", "-w", WALLET_DIR, *args]
    print("$", " ".join(a if not a.startswith("uview") else "uview1…" for a in cmd), flush=True)
    subprocess.run(cmd, check=True)


def sync():
    if not os.path.exists(os.path.join(WALLET_DIR, "data.sqlite")):
        shutil.rmtree(WALLET_DIR, ignore_errors=True)  # clear any half-made wallet
        ufvk = re.sub(r"\s+", "", os.environ["HW_UFVK"])        # pasted keys often carry a stray newline
        birthday = re.sub(r"\D", "", os.environ["HW_BIRTHDAY"])
        run("init-fvk", "--name", "hidden-witness", "--fvk", ufvk, "--birthday", birthday, "-s", LWD)
    run("sync", "-s", LWD)
    # Memos are not in compact blocks; enhance downloads full transactions and decrypts them.
    run("enhance", "-s", LWD)


def norm(s):
    """Answers compare case-, accent-, space- and punctuation-blind."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def memo_text(b):
    """ZIP 302: a first byte <= 0xF4 means UTF-8 text, padded with zero bytes."""
    if not b or b[0] > 0xF4:
        return None
    try:
        return bytes(b).rstrip(b"\x00").decode("utf-8")
    except UnicodeDecodeError:
        return None


FIELD_RE = re.compile(r"\b(round|seat|answer|code|reply)\s*[:=]\s*", re.I)


def parse(text):
    """Accepts the memo on separate lines, on one line, or split with "|".
    Many wallets flatten line breaks in memos, so field names are the anchors."""
    if not text or MEMO_TAG.lower() not in text.lower():
        return None
    body = text.replace("\r", " ").replace("\n", " | ")
    fields = {}
    marks = list(FIELD_RE.finditer(body))
    for n, m in enumerate(marks):
        end = marks[n + 1].start() if n + 1 < len(marks) else len(body)
        fields.setdefault(m.group(1).lower(), body[m.end():end].strip(" |\t"))
    seat = re.sub(r"\D", "", fields.get("seat", ""))[:4]
    reply = re.sub(r"\s+", "", fields.get("reply", ""))
    return {
        "round": re.sub(r"[^a-z0-9-]", "", fields.get("round", "").lower()),
        "seat": int(seat) if seat and 1 <= int(seat) <= 1000 else None,
        "answer": fields.get("code") or fields.get("answer", ""),
        "reply": reply if UA_RE.match(reply) else None,
    }


def claims():
    db = sqlite3.connect(os.path.join(WALLET_DIR, "data.sqlite"))
    rows = db.execute(
        """
        select o.txid, o.tx_mined_height, o.memo, o.value, o.output_pool, o.output_index, b.time
          from v_tx_outputs o
          left join blocks b on b.height = o.tx_mined_height
         where o.to_account_uuid is not null          -- received by the witness wallet
           and coalesce(o.is_change, 0) = 0
           and o.memo is not null and o.tx_mined_height is not null
           and o.output_pool in (2, 3, 4)             -- Sapling, Orchard or Ironwood: shielded only
         order by o.tx_mined_height, o.txid, o.output_index
        """
    ).fetchall()
    # Public-safe diagnostics (these logs are public): never print memo text, amounts or addresses.
    diag = db.execute(
        """
        select o.output_pool, o.memo is not null, substr(hex(o.memo), 1, 2), o.tx_mined_height is not null
          from v_tx_outputs o
         where o.to_account_uuid is not null and coalesce(o.is_change, 0) = 0
        """
    ).fetchall()
    for pool, has_memo, first, mined in diag:
        print(f"received output: pool={pool} mined={bool(mined)} memo={'yes' if has_memo else 'no'} memo_byte0={first or '-'}")
    tip = db.execute("select max(height) from blocks").fetchone()[0]
    db.close()
    seen = {}
    for txid, height, memo, value, pool, idx, btime in rows:
        txhex = bytes(txid)[::-1].hex()  # display order, as explorers show it
        if txhex in seen:
            continue
        c = parse(memo_text(memo))
        if c is None:
            t = memo_text(memo)
            print(f"  output in block {height}: memo is {'text without the game tag' if t else 'not text / empty'}")
        if c and value and value > 0:
            c.update(txid=txhex, height=height, time=btime)
            seen[txhex] = c
    return list(seen.values()), tip


def supa(method, path, body=None, prefer=None):
    url = os.environ["SUPABASE_URL"].strip().rstrip("/") + "/rest/v1/" + path
    key = re.sub(r"\s+", "", os.environ["SUPABASE_SERVICE_KEY"])
    headers = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("eyJ"):  # legacy JWT service_role key; new sb_secret_ keys go in apikey only
        headers["Authorization"] = "Bearer " + key
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as e:
        kind = "sb_secret" if key.startswith("sb_secret_") else "legacy JWT" if key.startswith("eyJ") else "publishable?" if key.startswith("sb_publishable_") else "unrecognised"
        print(f"supabase {method} {path.split('?')[0]} -> {e.code} (key type: {kind}): {e.read().decode()[:300]}", file=sys.stderr)
        raise


def iso(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat()


def ts(iso_str):
    return datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()


def player_id(reply):
    """A stable public tag for a player that doesn't reveal their address (keyed with the viewing key)."""
    key = re.sub(r"\s+", "", os.environ.get("HW_UFVK", "local")).encode()
    return hmac.new(key, reply.encode(), hashlib.sha256).hexdigest()[:12]


def load_drops(now):
    grace = float(os.environ.get("HW_GRACE_MINUTES", "5")) * 60
    drops = []
    for n, d in enumerate(json.loads(os.environ.get("HW_DROPS", "[]") or "[]"), 1):
        opens = ts(d["opens"])
        closes = opens + float(d.get("minutes", 60)) * 60
        drops.append({"id": d["id"], "n": n, "code": norm(d["code"]), "opens": opens,
                      "closes": closes, "until": closes + grace, "label": d.get("label") or f"Drop {n}"})
    codes = [d["code"] for d in drops]
    if len(codes) != len(set(codes)):
        raise SystemExit("two drops share a code; every code must be unique")
    return drops


def main():
    if os.environ.get("HW_SKIP_SYNC") != "1":
        sync()
    found, tip = claims()
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    # Some sync modes don't keep every block's time; estimate from the tip (75-second blocks).
    for c in found:
        if not c.get("time") and tip:
            c["time"] = now - (tip - c["height"]) * 75

    drops = load_drops(now)
    by_code = {d["code"]: d for d in drops}
    answers = {k.lower(): norm(v) for k, v in json.loads(os.environ.get("HW_ANSWERS", "{}") or "{}").items()}

    # Publish only the drops that have already opened: nothing public reveals a drop before it lands.
    round_rows = [{"id": d["id"], "label": d["label"], "is_open": d["opens"] <= now < d["closes"],
                   "opened_at": iso(d["opens"]), "closed_at": iso(d["closes"])}
                  for d in drops if d["opens"] <= now]
    rounds = {} if DRY else {r["id"]: r for r in supa("GET", "witness_rounds?select=*")}

    proofs, payouts, caught, rank = [], [], set(), {}
    for c in found:
        code = norm(c["answer"])
        d = by_code.get(code)
        pid = player_id(c["reply"]) if c["reply"] else None
        if d is not None:
            if d["opens"] > now or c["time"] < d["opens"]:
                continue  # mined before the drop existed: a test or a leak, ignored entirely
            in_window = c["time"] <= d["until"]
            ok = bool(in_window and pid and (pid, d["id"]) not in caught)
            pos = None
            if ok:
                caught.add((pid, d["id"]))
                rank[d["id"]] = rank.get(d["id"], 0) + 1
                pos = rank[d["id"]]
            proofs.append({"txid": c["txid"], "round_id": d["id"], "seat": c["seat"], "height": c["height"],
                           "ok": ok, "rank": pos, "player": pid})
            print(f"  claim at block {c['height']}: {d['label']}, "
                  f"{'in window' if in_window else 'late'}, {'caught' if ok else 'not counted'}")
        else:
            # Legacy riddle rounds (if any) or a wrong code.
            rnd = c["round"]
            r = rounds.get(rnd)
            if r and not r.get("opened_at"):
                continue
            if r and r.get("opened_at") and c["time"] < ts(r["opened_at"]):
                continue
            ok = bool(r and rnd in answers and answers[rnd] and code == answers[rnd])
            pos = None
            if ok:
                rank[rnd] = rank.get(rnd, 0) + 1
                pos = rank[rnd]
            proofs.append({"txid": c["txid"], "round_id": rnd if (r or DRY) and rnd else None, "seat": c["seat"],
                           "height": c["height"], "ok": ok, "rank": pos, "player": pid})
        if c["reply"]:
            payouts.append({"txid": c["txid"], "reply_to": c["reply"]})

    print(f"chain tip read: {tip}; drops opened: {len(round_rows)}; claims: {len(proofs)}; counted: {sum(p['ok'] for p in proofs)}")
    if DRY:
        for r in round_rows:
            print(json.dumps(r))
        for p in proofs:
            print(json.dumps(p))
        return
    if round_rows:
        supa("POST", "witness_rounds?on_conflict=id", round_rows, "resolution=merge-duplicates,return=minimal")
    if proofs:
        supa("POST", "witness_proofs?on_conflict=txid", proofs, "resolution=merge-duplicates,return=minimal")
    if payouts:
        supa("POST", "witness_payouts?on_conflict=txid", payouts, "resolution=ignore-duplicates,return=minimal")
    supa("PATCH", "witness_reader?id=eq.1", {"synced_height": tip, "synced_at": iso(now)}, "return=minimal")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print("devtool failed:", e, file=sys.stderr)
        sys.exit(1)
