-- THE HIDDEN WITNESS: private details.
-- Each caught clue unlocks one detail about the witness for that player only.
-- The page can read any row, but a row is useless without the key that rode inside the player's own shielded memo.
begin;
create table if not exists public.witness_whispers (
  tag        text primary key check (tag ~ '^[0-9a-f]{32}$'),
  box        text not null check (box ~ '^[0-9a-f]{2,512}$'),
  created_at timestamptz not null default now()
);
alter table public.witness_whispers enable row level security;
drop policy if exists "anyone can read sealed details" on public.witness_whispers;
create policy "anyone can read sealed details" on public.witness_whispers for select to anon, authenticated using (true);
grant select on public.witness_whispers to anon, authenticated;
commit;
-- The detail text for each clue lives in witness_secret (key 'details'), which only the reader can read.
