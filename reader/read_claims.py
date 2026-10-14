#!/usr/bin/env python3
"""THE HIDDEN WITNESS: the shielded claim reader.

Reads the game wallet with its viewing key (it can see, never spend), finds
claims sent as shielded Zcash payments, checks each sealed answer, and posts
only the public result to Supabase: round, seat, block, txid, correct or not.

The answer, the sender, the amount and the memo never leave this script.

Environment:
  HW_UFVK              the game wallet's unified full viewing key (uview1...)
  HW_BIRTHDAY          block height the game wallet was created at
  HW_ANSWERS           JSON: {"egg": "the answer", ...}  (kept secret)
  SUPABASE_URL         https://<project>.supabase.co
  SUPABASE_SERVICE_KEY service role key (kept secret; never in the page)
  DEVTOOL              path to the zcash-devtool binary
  WALLET_DIR           where the view-only wallet database lives
  HW_LWD               lightwalletd servers (default: zecrocks)
  HW_DRY_RUN=1         print results instead of writing them
"""

import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
import unicodedata
import urllib.request

DEVTOOL = os.environ.get("DEVTOOL", "zcash-devtool")
WALLET_DIR = os.environ.get("WALLET_DIR", "./hw_wallet")
LWD = os.environ.get("HW_LWD", "zecrocks")
DRY = os.environ.get("HW_DRY_RUN") == "1"

# The memo the page writes. Lines are "key: value"; order and spacing don't matter.
#   THE HIDDEN WITNESS
#   round: egg
#   seat: 214
#   answer: ...
#   reply: u1...            (optional: where to send the bounty)
MEMO_TAG = "THE HIDDEN WITNESS"
UA_RE = re.compile(r"^(u1|zs1)[0-9a-z]{20,}$")


def run(*args):
    cmd = [DEVTOOL, "wallet", "-w", WALLET_DIR, *args]
    print("$", " ".join(a if not a.startswith("uview") else "uview1…" for a in cmd), flush=True)
    subprocess.run(cmd, check=True)


def sync():
    if not os.path.exists(os.path.join(WALLET_DIR, "data.sqlite")):
        run("init-fvk", "--name", "hidden-witness", "--fvk", os.environ["HW_UFVK"],
            "--birthday", os.environ["HW_BIRTHDAY"], "-s", LWD)
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


def parse(text):
    if not text or MEMO_TAG.lower() not in text.lower():
        return None
    fields = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip().lower()] = v.strip()
    seat = re.sub(r"\D", "", fields.get("seat", ""))
    reply = fields.get("reply", "").strip()
    return {
        "round": fields.get("round", "").strip().lower(),
        "seat": int(seat) if seat and 1 <= int(seat) <= 1000 else None,
        "answer": fields.get("answer", ""),
        "reply": reply if UA_RE.match(reply) else None,
    }


def claims():
    db = sqlite3.connect(os.path.join(WALLET_DIR, "data.sqlite"))
    rows = db.execute(
        """
        select txid, mined_height, memo, value, output_pool, output_index
          from v_tx_outputs
         where is_sent_row = 0 and memo is not null and mined_height is not null
           and output_pool in (2, 3)          -- Sapling or Orchard: shielded only
         order by mined_height, txid, output_index
        """
    ).fetchall()
    tip = db.execute("select max(height) from blocks").fetchone()[0]
    db.close()
    seen = {}
    for txid, height, memo, value, pool, idx in rows:
        txhex = bytes(txid)[::-1].hex()  # display order, as explorers show it
        if txhex in seen:
            continue
        c = parse(memo_text(memo))
        if c and value and value > 0:
            c.update(txid=txhex, height=height)
            seen[txhex] = c
    return list(seen.values()), tip


def supa(method, path, body=None, prefer=None):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    key = os.environ["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt else None


def main():
    if os.environ.get("HW_SKIP_SYNC") != "1":
        sync()
    found, tip = claims()
    answers = {k.lower(): norm(v) for k, v in json.loads(os.environ.get("HW_ANSWERS", "{}")).items()}

    rounds = {} if DRY else {r["id"]: r for r in supa("GET", "witness_rounds?select=*")}
    proofs, payouts, rank = [], [], {}
    for c in found:
        rnd = c["round"]
        r = rounds.get(rnd)
        valid_round = DRY or (r is not None and (r.get("opened_at") or "") != "")
        ok = bool(valid_round and rnd in answers and answers[rnd] and norm(c["answer"]) == answers[rnd])
        pos = None
        if ok:
            rank[rnd] = rank.get(rnd, 0) + 1
            pos = rank[rnd]
            cap = (r or {}).get("max_proven")
            if cap and pos > cap:
                ok, pos = False, None
        proofs.append({"txid": c["txid"], "round_id": rnd if (DRY or rnd in rounds) else None,
                       "seat": c["seat"], "height": c["height"], "ok": ok, "rank": pos})
        if c["reply"]:
            payouts.append({"txid": c["txid"], "reply_to": c["reply"]})

    print(f"chain tip read: {tip}; claims found: {len(proofs)}; proven: {sum(p['ok'] for p in proofs)}")
    if DRY:
        for p in proofs:
            print(json.dumps(p))
        return
    if proofs:
        supa("POST", "witness_proofs?on_conflict=txid", proofs, "resolution=merge-duplicates,return=minimal")
    if payouts:
        supa("POST", "witness_payouts?on_conflict=txid", payouts, "resolution=ignore-duplicates,return=minimal")
    supa("PATCH", "witness_reader?id=eq.1", {"synced_height": tip, "synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}, "return=minimal")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print("devtool failed:", e, file=sys.stderr)
        sys.exit(1)
