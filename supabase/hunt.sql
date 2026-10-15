-- THE HIDDEN WITNESS: the hunt (clues, crossing off, one sealed guess).
begin;

-- Private game settings: only the reader (service key) can read them. No public policy.
create table if not exists public.witness_secret (
  key   text primary key,
  value text not null
);
alter table public.witness_secret enable row level security;

-- The guess round (proofs of guesses point at it).
insert into public.witness_rounds (id, label, is_open) values ('accuse', 'The guess', false)
on conflict (id) do nothing;

-- Public bucket for the game's own copy of every crowd picture.
insert into storage.buckets (id, name, public) values ('crowd', 'crowd', true)
on conflict (id) do nothing;

commit;
-- Settings (schedule, witness, season_opens) are inserted separately, in the SQL editor, never in this repo.
