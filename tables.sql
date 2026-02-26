create table documents (
  id uuid primary key default gen_random_uuid(),
  file_name text not null,
  file_path text not null,
  status text default 'processing',
  created_at timestamp default now()
);

create table document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  page_number int,
  raw_text text,
  created_at timestamp default now()
);

drop table if exists document_chunks;

create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  page_number int,
  content text,
  embedding vector(768),
  created_at timestamp default now()
);

create table if not exists public.extracted_metrics (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references public.documents(id) on delete cascade,
  purchase_price numeric,
  noi numeric,
  cap_rate numeric,
  occupancy numeric,
  units int,
  year_built int,
  property_type text,
  location text,
  risk_summary text,
  created_at timestamp default now()
);


create or replace function match_document_chunks(
  query_embedding vector(768),
  doc_id uuid,
  match_count int
)
returns table (
  id uuid,
  content text,
  page_number int,
  similarity float
)
language sql
as $$
  select
    id,
    content,
    page_number,
    1 - (embedding <=> query_embedding) as similarity
  from document_chunks
  where document_id = doc_id
  order by embedding <=> query_embedding
  limit match_count;
$$;