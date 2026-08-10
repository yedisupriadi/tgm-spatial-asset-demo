-- TGM Spatial Asset - Supabase/PostGIS starter schema
-- Run later in Supabase SQL Editor after enabling PostGIS.
-- This file is NOT required for the local demo.

create extension if not exists postgis;

create table if not exists public.spatial_assets (
  id uuid primary key default gen_random_uuid(),
  asset_code text not null unique,
  title text not null,
  asset_type text not null check (asset_type in ('LAND', 'HOUSE', 'COMMERCIAL')),
  status text not null default 'AVAILABLE'
    check (status in ('AVAILABLE', 'RESERVED', 'SOLD')),
  price_idr numeric(18,2),
  area_m2 numeric(18,2),
  source text,
  notes text,
  geometry geometry(Polygon, 4326) not null,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists spatial_assets_geometry_gix
on public.spatial_assets
using gist (geometry);

alter table public.spatial_assets enable row level security;

-- READ EXAMPLE:
-- In production, replace this broad policy with project/company membership rules.
create policy "authenticated users can read spatial assets"
on public.spatial_assets
for select
to authenticated
using (true);

-- WRITE EXAMPLE:
-- Start restrictive. Later connect this to roles such as admin / asset_manager.
create policy "authenticated users can create spatial assets"
on public.spatial_assets
for insert
to authenticated
with check (auth.uid() = created_by);

create policy "creator can update own spatial assets"
on public.spatial_assets
for update
to authenticated
using (auth.uid() = created_by)
with check (auth.uid() = created_by);
