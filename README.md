# THE HIDDEN WITNESS

**A zero-knowledge game where the proof is a shielded Zcash transaction.**
By chris berlin (Berlin Studios), built for ZECATHON by zkSNARKs. Wildcard track.

Live: https://yhnybxsq.srstudio.dev/ (SuperRare Studio)

---

## The idea

Somewhere in a crowd of up to 1,000 faces is a witness. Players take a free seat, and then the game happens on X.

**The drops.** Seven times, at odd hours and without warning, a post lands on @chrisberlin marked with ⌖. It carries a code. The code lives for 60 minutes, then the post is deleted and the drop is never repeated. To catch it, a player seals the code inside a shielded Zcash payment that is mined before the hour runs out.

No riddle, nothing to compute, nothing an AI can solve in advance. The only way to win is to be there: notifications on, paying attention, acting inside the hour. The game rewards participation.

## Why the shielded transaction is worth making

- **The chain is the clock.** A catch counts if the block holding the payment is timestamped inside the window (plus 5 minutes' grace for mining). No server clock, no trust in the organiser, no "I sent it in time, honest".
- **Private.** The code, the sender, the amount and the player's address are encrypted on chain. Only the game's viewing key can read them.
- **Your shielded address is your identity.** Each player puts their own Zcash address in the memo. That is how catches add up across drops, and it is where prizes are paid, privately, without ever learning who the player is. The public board only shows a keyed hash of it, labelled with the player's seat.
- **Publicly countable.** Every catch on the board is a real shielded transaction. Anyone can count them; no one can read them.

Taking a seat is free and needs no wallet. Catching a drop takes one tiny shielded payment (0.001 ZEC plus the network fee), because that is the move that has to be private and timestamped.

## How it works

```
 player's wallet                 Zcash chain                  reader (GitHub Actions)              page
 ───────────────                 ───────────                  ───────────────────────              ────
 scans QR / ZIP-321 URI  ──►  shielded tx, memo encrypted  ──►  view-only wallet (UFVK)             proof board
 memo: round, seat,              to the witness address         syncs via lightwalletd     ──►      seat, block,
 answer, optional reply                                         decrypts memo, checks answer        txid, proven?
```

1. **The page** (`site/index.html`) builds the memo (`THE HIDDEN WITNESS | seat: 214 | code: … | reply: u1…`) and a [ZIP-321](https://zips.z.cash/zip-0321) payment URI with the memo base64url-encoded, shown as a QR code and an "open in wallet" link. The page never learns whether a code is right, or when the next drop is.
2. **The player** sends 0.001 ZEC from any shielded wallet. The memo is encrypted to the witness address.
3. **The reader** (`reader/read_claims.py`) runs every five minutes on GitHub Actions. It holds only the wallet's **unified full viewing key**, so it can see incoming payments but can never spend. It syncs with [`zcash-devtool`](https://github.com/zcash/zcash-devtool) (`init-fvk`, `sync`, `enhance`), reads shielded outputs only (Sapling, Orchard and Ironwood), decodes ZIP-302 text memos, matches each code to its drop, and checks the block's timestamp against that drop's window. Each player catches each drop once.
4. **Supabase** stores the public result only: drop, seat, block height, txid, caught or not, and a keyed hash of the player. The code, amount, sender and memo never leave the reader. Reply addresses go to a table with no public access.
5. **The board** on the page shows each drop once it has landed (never before), how many caught it, and the most-caught players by seat.

## Drops

The schedule (codes and opening times) lives only in a GitHub secret, `HW_DROPS`. Nothing public reveals a drop before it lands: the reader publishes each drop to the board only once it has opened. The door on the page opens for the whole season with one switch (`witness_rounds.id = 'drops'`).

## Repo

| Path | What it is |
|---|---|
| `site/index.html` | The whole game page: crowd, seats, proof door, proof board. One file. |
| `reader/read_claims.py` | The view-only claim reader. |
| `.github/workflows/reader.yml` | Runs the reader every five minutes. |
| `supabase/proofs.sql` | Tables and access rules for rounds, proofs, payouts and the reader heartbeat. |
| `supabase/drops.sql` | The player tag and the season switch for the drops. |

### Secrets (GitHub → Settings → Secrets and variables → Actions)

| Name | What |
|---|---|
| `HW_UFVK` | The witness wallet's unified full viewing key (`uview1…`). View-only. |
| `HW_BIRTHDAY` | Block height the witness wallet was created at. |
| `HW_DROPS` | The drop schedule: `[{"id": "d1", "code": "…", "opens": "2026-10-16T03:17:00-07:00", "minutes": 60}, …]`. |
| `HW_ANSWERS` | Optional, legacy riddle rounds. |
| `SUPABASE_URL` | The Supabase project URL. |
| `SUPABASE_SERVICE_KEY` | Supabase service role key, used only by the reader. |

Nothing secret is in this repository. The page uses only Supabase's public key, which can read the public tables and nothing else.

### Run the reader locally

```
cargo install --git https://github.com/zcash/zcash-devtool --rev 5a26ee854e634a4e88d1d79dab13f8fbb1eac6b8
HW_UFVK=uview1… HW_BIRTHDAY=… HW_DROPS='[…]' HW_DRY_RUN=1 \
  DEVTOOL=zcash-devtool python3 reader/read_claims.py
```

## Credits

- [zcash-devtool](https://github.com/zcash/zcash-devtool) (MIT/Apache-2.0) for view-only sync and memo decryption.
- [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) by Kazuhiko Arase (MIT), inlined in the page.
- Inspired by the zkSNARKs team. Not affiliated with the zkSNARKs team or Electric Coin Co.

## License

Code: MIT. The artwork, logo and seat-card art are © chris berlin, all rights reserved.
