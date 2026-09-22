-- DemoBoard: posts table + RLS policies for Supabase
-- Run this in the Supabase project's SQL editor (or via `supabase db push`).

create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  author text not null,
  content text not null,
  views integer not null default 0,
  created_at timestamptz not null default now()
);

alter table public.posts enable row level security;

-- DemoBoard has no auth, so allow public access via the anon key.
create policy "Public read access" on public.posts
  for select using (true);

create policy "Public insert access" on public.posts
  for insert with check (true);

create policy "Public update access" on public.posts
  for update using (true) with check (true);

create policy "Public delete access" on public.posts
  for delete using (true);

-- Atomic view counter, used instead of read-then-write from the client.
create or replace function public.increment_post_views(post_id uuid)
returns void
language sql
as $$
  update public.posts set views = views + 1 where id = post_id;
$$;

-- Seed data matching the original demo content (optional).
insert into public.posts (title, author, content, views, created_at)
values
  (
    'DemoBoard에 오신 것을 환영합니다',
    '관리자',
    'Next.js, shadcn/ui, TypeScript로 만든 게시판입니다. 자유롭게 글을 작성해 보세요.',
    12,
    '2026-09-01T09:00:00.000Z'
  ),
  (
    '공지사항: 이용 안내',
    '관리자',
    '게시글 작성, 수정, 삭제가 가능합니다. 우측 상단의 글쓰기 버튼을 눌러 시작하세요.',
    5,
    '2026-09-05T09:00:00.000Z'
  )
on conflict do nothing;
