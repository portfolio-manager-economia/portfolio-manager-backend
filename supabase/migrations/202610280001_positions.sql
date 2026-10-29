-- Run once in a NEW Supabase project's SQL editor, or with supabase db push.
begin;
create table public.positions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
    ticker text not null check (ticker ~ '^[A-Z0-9.^=\-]{1,30}$'),
    asset_type text not null check (asset_type in ('stock', 'cedear', 'crypto', 'bond')),
    currency text not null check (currency in ('ARS', 'USD')),
    quantity numeric not null check (quantity > 0 and quantity < 'Infinity'::numeric),
    buy_price numeric not null check (buy_price > 0 and buy_price < 'Infinity'::numeric),
    buy_fx_rate numeric not null check (buy_fx_rate > 0 and buy_fx_rate < 'Infinity'::numeric),
    buy_date date not null,
    created_at timestamptz not null default now()
);
create index positions_user_id_idx on public.positions(user_id);
alter table public.positions enable row level security;
revoke all on public.positions from anon, authenticated;
grant select, insert, delete on public.positions to authenticated;
create policy "Read own positions" on public.positions for select to authenticated
    using ((select auth.uid()) = user_id);
create policy "Insert own positions" on public.positions for insert to authenticated
    with check ((select auth.uid()) = user_id);
create policy "Delete own positions" on public.positions for delete to authenticated
    using ((select auth.uid()) = user_id);
commit;
