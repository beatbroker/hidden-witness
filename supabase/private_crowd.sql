-- THE HIDDEN WITNESS: keep join order private.
-- The public can see the faces and a seat count, never when anyone joined.

begin;

-- Faces only. No id, no join time, in an order that says nothing about when anyone joined.
create or replace view public.crowd as
  select handle, shielded, avatar
  from public.witnesses
  order by md5(coalesce(avatar, '') || coalesce(handle, ''));
grant select on public.crowd to anon, authenticated;

-- How many seats are taken (distinct faces since seat cards began).
create or replace function public.seats_taken() returns integer
  language sql stable security definer set search_path = public as $$
  select count(distinct avatar)::int from public.witnesses
  where ts > '2026-09-29T01:10:00Z' and avatar is not null
$$;
revoke all on function public.seats_taken() from public;
grant execute on function public.seats_taken() to anon, authenticated;

commit;

-- Step 2, once the page reads from the view: the raw table can be written to, never read.
--   revoke select on public.witnesses from anon, authenticated;
