create table if not exists public.feedback_events (
  event_id uuid primary key,
  workspace text not null default 'design-daily' check (workspace = 'design-daily'),
  actor_id text not null check (char_length(actor_id) between 1 and 128),
  product_id text not null check (char_length(product_id) between 1 and 2048),
  action text not null check (action in ('like', 'pass', 'clear')),
  reason text not null default '',
  context jsonb not null default '{}'::jsonb,
  item_snapshot jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  received_at timestamptz not null default now(),
  constraint feedback_reason_check check (
    (
      action = 'pass'
      and reason in (
        'too_ordinary',
        'weak_function',
        'wrong_category',
        'low_margin',
        'hard_to_execute',
        'bad_evidence'
      )
    )
    or (action in ('like', 'clear') and reason = '')
  ),
  constraint feedback_context_size check (octet_length(context::text) <= 8192),
  constraint feedback_snapshot_size check (octet_length(item_snapshot::text) <= 16384)
);

create index if not exists feedback_events_workspace_created_idx
  on public.feedback_events (workspace, created_at desc);
create index if not exists feedback_events_product_idx
  on public.feedback_events (workspace, product_id, created_at desc);
create index if not exists feedback_events_actor_idx
  on public.feedback_events (actor_id, received_at desc);

alter table public.feedback_events enable row level security;
revoke all on table public.feedback_events from anon, authenticated;
grant usage on schema public to anon, authenticated;
grant insert on table public.feedback_events to anon, authenticated;

drop policy if exists "anonymous feedback insert" on public.feedback_events;
create policy "anonymous feedback insert"
on public.feedback_events
for insert
to anon, authenticated
with check (
  workspace = 'design-daily'
  and action in ('like', 'pass', 'clear')
  and created_at >= now() - interval '30 days'
  and created_at <= now() + interval '10 minutes'
);

create or replace function public.guard_feedback_rate()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if (
    select count(*)
    from public.feedback_events
    where actor_id = new.actor_id
      and received_at >= date_trunc('day', now())
  ) >= 200 then
    raise exception 'daily feedback limit reached';
  end if;
  return new;
end;
$$;

revoke all on function public.guard_feedback_rate() from public, anon, authenticated;
drop trigger if exists feedback_rate_guard on public.feedback_events;
create trigger feedback_rate_guard
before insert on public.feedback_events
for each row execute function public.guard_feedback_rate();
