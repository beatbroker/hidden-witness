# THE HIDDEN WITNESS

**A hunt where every move is a shielded Zcash transaction.**
By chris berlin (Berlin Studios). Built for ZECATHON by zkSNARKs, Wildcard track.

**Play:** https://yhnybxsq.srstudio.dev/ · **Follow:** [@chrisberlin](https://x.com/chrisberlin)

---

## The 60-second version

- A crowd of faces. **One of them is the witness.**
- **Take a seat.** It's free and needs no wallet. The doors close on **Halloween, Oct 31**. After that, nobody new gets in.
- **Seven clues** drop on X at odd hours, starting **Nov 1**. Each one lives for 60 minutes, then it's gone forever.
- **Catch a clue** by sealing its code inside a shielded Zcash message before the hour runs out. The blockchain is the clock.
- **Every catch unlocks a private detail** about the witness, readable only by the player who caught it.
- **One guess per player**, sealed so nobody can see it or copy it. The first right answer wins.

No riddles. Nothing an AI can solve for you. The public clues only get you close. **Showing up is what wins.**

---

## How a round plays

**1. The crowd fills (now → Oct 31).**
Players take a seat with their X handle, and their picture joins the crowd. They can choose to stay shielded, which puts their face in the crowd with no name attached. Between Oct 22 and 29, eight unnamed faces sit down one a day. They look almost exactly alike. One of them is the witness.

**2. The doors close (Oct 31, midnight Pacific).**
The game begins on its own. No new seats after that.

**3. Seven clues (Nov 1 → Nov 9).**
Each clue on X carries a code and one public line about the witness ("The witness covers its head"). Players use the "cross off faces" tool on the page to rule people out. Read all seven public lines and you're down to the eight lookalikes. Public information goes no further than that.

**4. Catches unlock private details.**
To catch a clue, a player seals its code in a shielded message within the hour. When the catch counts, the page shows that player one private detail that rules out one lookalike. Catch more clues and you have fewer suspects. Catch all seven and you have one.

**5. One sealed guess.**
Any player can guess at any time, and a guess counts if that player caught at least 3 clues. Guesses stay sealed until the last clue's hour ends, then the first correct guess on chain wins. Guess early with fewer details and you might beat everyone. Wait, and you're certain but late.

---

## Why the shielded transaction is worth making

| | |
|---|---|
| **The chain is the clock** | A catch counts if the block holding it is timestamped inside the window. No server clock, no trusting the organiser. |
| **Private by default** | The code, the sender, the amount and the player's address are encrypted on chain. |
| **Sealed guesses** | Nobody can see anyone's guess, so nobody can copy it. |
| **Private details** | Each detail is locked to a key that rides only inside the player's own shielded memo. Showing up gives you information a screenshot never can. |
| **Countable, not readable** | Every catch on the public board is a real shielded transaction. Anyone can count them. No one can read them. |
| **View-only** | The game reads the chain with a viewing key. It can see. It can never spend. |

Taking a seat costs nothing. Each catch or guess is one tiny shielded message (0.0001 ZEC plus the network fee). That is the move that has to be private and timestamped.

---

## Key dates (Pacific)

| When | What |
|---|---|
| Now | Seats open, free |
| Oct 22 → 29 | One unnamed face sits down each day |
| Oct 31, midnight | Doors close, the game begins |
| Nov 1 → Nov 9 | Seven clues at odd hours, 60 minutes each |
| Nov 9 | Guesses unseal; the first right answer wins |

---

## Under the hood

```
 player's wallet                 Zcash chain                     reader (GitHub Actions)               page
 ───────────────                 ───────────                     ───────────────────────               ────
 scans QR / ZIP-321 URI  ──►  shielded tx, memo encrypted  ──►  view-only wallet (UFVK)      ──►      board: seat, block,
 memo: seat, code,               to the game address             syncs via lightwalletd               caught or not
 reply address, key                                              decodes memo, checks code             + your private details
                                                                 seals a detail for your key
```

1. **The page** (`site/index.html`) builds the memo (`THE HIDDEN WITNESS | seat: 214 | code: … | reply: u1… | key: …`) and a [ZIP-321](https://zips.z.cash/zip-0321) payment URI, shown as a QR code and an "open in wallet" link. The page never knows whether a code is right, when the next clue lands, or which face is the witness.
2. **The player** sends it from any shielded wallet (Zashi, Zingo, Zkool…).
3. **The reader** (`reader/read_claims.py`) runs every five minutes on GitHub Actions. It holds only the wallet's **unified full viewing key**. It syncs with [`zcash-devtool`](https://github.com/zcash/zcash-devtool), reads shielded outputs only, decodes ZIP-302 text memos, and checks each code against its clue's window using the block's own timestamp.
4. **Private details.** For each counted catch, the reader encrypts that clue's detail with the player's key from the memo and stores only the sealed result (`witness_whispers`). The page re-derives the key in the player's browser and opens it. Without the key, a row is noise.
5. **Supabase** stores public results only: clue, seat, block, txid, caught or not, and a keyed hash of the player. Answers, the schedule and the witness live in a table (`witness_secret`) that only the reader can read.

### Repo

| Path | What it is |
|---|---|
| `site/index.html` | The whole game page: crowd, seats, hunt, look-closer view, catch form, guess, board, private details. |
| `site/house/` | The eight unnamed faces. |
| `reader/read_claims.py` | The view-only reader. |
| `.github/workflows/` | `reader.yml` (5-minute timer) and `keeper.yml` (a self-restarting job that reads every 5 minutes). |
| `supabase/*.sql` | Tables and access rules: proofs, clues, the hunt, the private crowd view, sealed details. |

Nothing secret is in this repository. The page uses only Supabase's public key, which can read public tables and nothing else.

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

Code: MIT. The artwork, logo, faces and seat-card art are © chris berlin, all rights reserved.
