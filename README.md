# THE HIDDEN WITNESS

**A zero-knowledge game where the proof is a shielded Zcash transaction.**
By chris berlin (Berlin Studios), built for ZECATHON by zkSNARKs. Wildcard track.

Live: https://yhnybxsq.srstudio.dev/ (SuperRare Studio)

---

## The idea

Somewhere in a crowd of up to 1,000 faces is a witness. Players take a free seat, follow clues that drop on X, find the witness, and then have to **prove they found it without revealing where it is**.

That proof is a real shielded Zcash payment. The player's answer rides inside the transaction's **encrypted memo**, sealed to their seat number. The chain records a valid payment and nothing else: not who sent it, not what it says, not which seat it came from.

## Why the shielded transaction is worth making

In a public puzzle hunt, the first person to post a correct answer gives it away to everyone behind them. Here, there is no way to win *except* with a shielded transaction:

- **Private:** the answer is encrypted on chain. Only the game's viewing key can read it.
- **Uncopyable:** nobody can see anyone else's answer, so nobody can copy it.
- **Timestamped:** block order decides who proved it first. No server clock, no trust in the organiser's inbox.
- **Publicly checkable:** every proof on the board links to its transaction. Anyone can verify it exists on chain; no one can read it.
- **Paid back privately:** a player can add their own shielded address to the memo, so a prize reaches them without ever revealing who they are.

Taking a seat is free and needs no wallet. The shielded transaction is the one move that has to be private, so it is the one move that costs anything (0.001 ZEC plus the network fee).

## How it works

```
 player's wallet                 Zcash chain                  reader (GitHub Actions)              page
 ───────────────                 ───────────                  ───────────────────────              ────
 scans QR / ZIP-321 URI  ──►  shielded tx, memo encrypted  ──►  view-only wallet (UFVK)             proof board
 memo: round, seat,              to the witness address         syncs via lightwalletd     ──►      seat, block,
 answer, optional reply                                         decrypts memo, checks answer        txid, proven?
```

1. **The page** (`site/index.html`) builds the memo and a [ZIP-321](https://zips.z.cash/zip-0321) payment URI with the memo base64url-encoded, shown as a QR code and an "open in wallet" link. The page never learns whether an answer is right.
2. **The player** sends 0.001 ZEC from any shielded wallet. The memo is encrypted to the witness address.
3. **The reader** (`reader/read_claims.py`) runs every five minutes on GitHub Actions. It holds only the wallet's **unified full viewing key**, so it can see incoming payments but can never spend. It syncs with [`zcash-devtool`](https://github.com/zcash/zcash-devtool) (`init-fvk`, `sync`, `enhance`), reads shielded outputs only (Sapling, Orchard and Ironwood), decodes ZIP-302 text memos, and compares each answer with the round's secret answer.
4. **Supabase** stores the public result only: round, seat, block height, txid, correct or not, and rank. The answer, amount, sender and memo never leave the reader. Reply addresses go to a table with no public access.
5. **The proof board** on the page shows sealed and proven counts, the order of correct proofs, and when the reader last read the chain.

## Rounds

- **The shielded Easter egg** opens before the doors close on Halloween, so the proof door is live and used on mainnet.
- **The hunt** opens when the doors close: October 31, or sooner if all 1,000 seats fill. It uses the same door.

Rounds open and close from the `witness_rounds` table, so a new clue never needs a redeploy.

## Repo

| Path | What it is |
|---|---|
| `site/index.html` | The whole game page: crowd, seats, proof door, proof board. One file. |
| `reader/read_claims.py` | The view-only claim reader. |
| `.github/workflows/reader.yml` | Runs the reader every five minutes. |
| `supabase/proofs.sql` | Tables and access rules for rounds, proofs, payouts and the reader heartbeat. |

### Secrets (GitHub → Settings → Secrets and variables → Actions)

| Name | What |
|---|---|
| `HW_UFVK` | The witness wallet's unified full viewing key (`uview1…`). View-only. |
| `HW_BIRTHDAY` | Block height the witness wallet was created at. |
| `HW_ANSWERS` | JSON of round answers, e.g. `{"egg": "…"}`. |
| `SUPABASE_URL` | The Supabase project URL. |
| `SUPABASE_SERVICE_KEY` | Supabase service role key, used only by the reader. |

Nothing secret is in this repository. The page uses only Supabase's public key, which can read the public tables and nothing else.

### Run the reader locally

```
cargo install --git https://github.com/zcash/zcash-devtool --rev 5a26ee854e634a4e88d1d79dab13f8fbb1eac6b8
HW_UFVK=uview1… HW_BIRTHDAY=… HW_ANSWERS='{"egg":"…"}' HW_DRY_RUN=1 \
  DEVTOOL=zcash-devtool python3 reader/read_claims.py
```

## Credits

- [zcash-devtool](https://github.com/zcash/zcash-devtool) (MIT/Apache-2.0) for view-only sync and memo decryption.
- [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) by Kazuhiko Arase (MIT), inlined in the page.
- Inspired by the zkSNARKs team. Not affiliated with the zkSNARKs team or Electric Coin Co.

## License

Code: MIT. The artwork, logo and seat-card art are © chris berlin, all rights reserved.
