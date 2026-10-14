-- THE HIDDEN WITNESS: shielded proofs.
-- Paste into Supabase > SQL Editor > New query, then Run. All or nothing.
-- Adds new tables only. The existing `witnesses` crowd table is not touched.

begin;

-- Rounds: each puzzle the crowd can prove. The page only offers the door for a round that is open.
create table if not exists public.witness_rounds (
  id         text primary key check (id ~ '^[a-z0-9-]{1,24}$'),
  label      text not null,
  is_open    boolean not null default false,
  opened_at  timestamptz,
  closed_at  timestamptz,
  max_proven integer        -- optional cap on how many proofs can win this round
);

-- Proofs: one row per shielded claim the reader has seen on chain.
-- Public: the round, the seat it was sealed to, the block, the txid, and whether it was correct.
-- Never public: the answer, the sender, the amount, or the memo.
create table if not exists public.witness_proofs (
  txid       text primary key check (txid ~ '^[0-9a-f]{64}$'),
  round_id   text references public.witness_rounds(id),
  seat       integer check (seat between 1 and 1000),
  height     integer not null,
  ok         boolean not null,
  rank       integer,         -- 1 = first correct proof of the round
  seen_at    timestamptz not null default now()
);
create index if not exists witness_proofs_round on public.witness_proofs (round_id, ok, height);

-- Private: where to pay winners. No public policy, so only the reader (service role) can read or write it.
create table if not exists public.witness_payouts (
  txid       text primary key references public.witness_proofs(txid),
  reply_to   text,
  paid_txid  text,
  note       text
);

-- Reader heartbeat, so the page can show when the chain was last read.
create table if not exists public.witness_reader (
  id         smallint primary key default 1 check (id = 1),
  synced_height integer,
  synced_at  timestamptz
);
insert into public.witness_reader (id) values (1) on conflict do nothing;

alter table public.witness_rounds  enable row level security;
alter table public.witness_proofs  enable row level security;
alter table public.witness_payouts enable row level security;
alter table public.witness_reader  enable row level security;

drop policy if exists "rounds are public" on public.witness_rounds;
create policy "rounds are public" on public.witness_rounds for select using (true);
drop policy if exists "proofs are public" on public.witness_proofs;
create policy "proofs are public" on public.witness_proofs for select using (true);
drop policy if exists "reader is public" on public.witness_reader;
create policy "reader is public" on public.witness_reader for select using (true);
-- witness_payouts: no policies on purpose.

-- The first round: the shielded Easter egg. Closed until Chris opens it.
insert into public.witness_rounds (id, label, is_open)
values ('egg', 'The shielded Easter egg', false)
on conflict (id) do nothing;

commit;

-- To open the Easter egg when you announce it:
--   update public.witness_rounds set is_open = true, opened_at = now() where id = 'egg';
-- To close it:
--   update public.witness_rounds set is_open = false, closed_at = now() where id = 'egg';
