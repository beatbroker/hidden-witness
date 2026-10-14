-- THE HIDDEN WITNESS: the drops.
-- Adds a player tag to proofs (a keyed hash of the player's shielded address, never the address itself)
-- and the season switch that opens the door on the page.
begin;
alter table public.witness_proofs add column if not exists player text check (player is null or player ~ '^[0-9a-f]{12}$');
create index if not exists witness_proofs_player on public.witness_proofs (player);
insert into public.witness_rounds (id, label, is_open) values ('drops', 'The drops', false)
on conflict (id) do nothing;
commit;

-- Open the season (the door appears on the page):
--   update public.witness_rounds set is_open = true, opened_at = now() where id = 'drops';
-- Individual drops (d1..d7) are published by the reader only once each one has opened.
