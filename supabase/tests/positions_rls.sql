-- Run AFTER the migration in the SQL editor of the NEW development project.
-- Everything, including the two temporary users, is rolled back.
begin;
insert into auth.users (id, email) values
    ('00000000-0000-0000-0000-000000000001', 'rls-test-a@example.invalid'),
    ('00000000-0000-0000-0000-000000000002', 'rls-test-b@example.invalid');
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000001","role":"authenticated"}', true);
insert into public.positions (id, ticker, asset_type, currency, quantity, buy_price, buy_fx_rate, buy_date)
values ('00000000-0000-0000-0000-000000000011', 'AAPL', 'stock', 'USD', 1, 100, 1, '2024-01-01');
do $$ begin
    if (select count(*) from public.positions) <> 1 then
        raise exception 'FAIL: user A cannot read own position';
    end if;
end $$;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000002","role":"authenticated"}', true);
do $$ begin
    if exists (select 1 from public.positions) then
        raise exception 'FAIL: user B can read user A positions';
    end if;
    delete from public.positions where id = '00000000-0000-0000-0000-000000000011';
    if found then raise exception 'FAIL: user B can delete user A position'; end if;
    begin
        insert into public.positions (user_id, ticker, asset_type, currency, quantity, buy_price, buy_fx_rate, buy_date)
        values ('00000000-0000-0000-0000-000000000001', 'AAPL', 'stock', 'USD', 1, 100, 1, '2024-01-01');
        raise exception 'FAIL: user B can insert as user A';
    exception when insufficient_privilege then null;
    end;
end $$;
set local role anon;
do $$ begin
    begin
        perform 1 from public.positions;
        raise exception 'FAIL: anonymous role can access positions';
    exception when insufficient_privilege then null;
    end;
end $$;
reset role;
rollback;
