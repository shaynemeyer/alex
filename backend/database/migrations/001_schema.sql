-- Alex Financial Planner Database Schema
-- Version: 001
-- Run in the Supabase SQL editor or via run_migrations.py

-- Core tables

create table if not exists users (
    clerk_user_id            text    primary key,
    display_name             text,
    years_until_retirement   integer,
    target_retirement_income decimal,
    asset_class_targets      jsonb default '{"equity": 70, "fixed_income": 30}',
    region_targets           jsonb default '{"north_america": 50, "international": 50}',
    created_at               timestamptz not null default now(),
    updated_at               timestamptz not null default now()
);

create table if not exists instruments (
    symbol                 text    primary key,
    name                   text    not null,
    instrument_type        text,
    current_price          decimal,
    allocation_regions     jsonb default '{}',
    allocation_sectors     jsonb default '{}',
    allocation_asset_class jsonb default '{}',
    created_at             timestamptz not null default now(),
    updated_at             timestamptz not null default now()
);

create table if not exists accounts (
    id              uuid    primary key default gen_random_uuid(),
    clerk_user_id   text    references users(clerk_user_id) on delete cascade,
    account_name    text    not null,
    account_purpose text,
    cash_balance    decimal default 0,
    cash_interest   decimal default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create table if not exists positions (
    id         uuid    primary key default gen_random_uuid(),
    account_id uuid    references accounts(id) on delete cascade,
    symbol     text    references instruments(symbol),
    quantity   decimal not null,
    as_of_date date    default current_date,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(account_id, symbol)
);

create table if not exists jobs (
    id                 uuid        primary key default gen_random_uuid(),
    clerk_user_id      text        references users(clerk_user_id) on delete cascade,
    job_type           text        not null,
    status             text        not null default 'pending',
    request_payload    jsonb,
    report_payload     jsonb,
    charts_payload     jsonb,
    retirement_payload jsonb,
    summary_payload    jsonb,
    error_message      text,
    created_at         timestamptz not null default now(),
    started_at         timestamptz,
    completed_at       timestamptz,
    updated_at         timestamptz not null default now()
);

-- Research data (from ingest pipeline)
create table if not exists research_documents (
    id            uuid        primary key default gen_random_uuid(),
    vector_id     text        not null,
    topic         text,
    full_text     text        not null,
    bullet_points text[]      not null default '{}',
    researched_at timestamptz,
    created_at    timestamptz not null default now()
);

-- Indexes
create index if not exists idx_accounts_user     on accounts(clerk_user_id);
create index if not exists idx_positions_account on positions(account_id);
create index if not exists idx_positions_symbol  on positions(symbol);
create index if not exists idx_jobs_user         on jobs(clerk_user_id);
create index if not exists idx_jobs_status       on jobs(status);
