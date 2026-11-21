-- TGM Spatial Asset - Supabase/PostGIS schema
-- NOTE: CREATE TABLE IF NOT EXISTS does not migrate an existing geometry type or status check.
-- Review and apply a separate vetted migration before production import of UNVERIFIED parcels.
-- Run in Supabase SQL Editor after reviewing the target project.
-- PostGIS docs: use geometry/geography types and GiST spatial indexes.

create extension if not exists postgis with schema extensions;

create table if not exists public.administrative_regions (
  code text primary key,
  name text not null,
  level text not null check (level in ('PROVINCE','REGENCY','DISTRICT','VILLAGE')),
  parent_code text references public.administrative_regions(code),
  capital text,
  latitude double precision,
  longitude double precision,
  area_km2 double precision,
  population bigint,
  boundary extensions.geometry(MultiPolygon, 4326),
  source text,
  source_reference text,
  updated_at timestamptz not null default now()
);

create index if not exists administrative_regions_parent_idx
on public.administrative_regions(parent_code);

create index if not exists administrative_regions_boundary_gix
on public.administrative_regions using gist(boundary);

create table if not exists public.spatial_assets (
  id uuid primary key default gen_random_uuid(),
  asset_code text not null unique,
  title text not null,
  asset_type text not null check (asset_type in ('LAND','HOUSE','BUILDING','COMMERCIAL')),
  status text not null default 'AVAILABLE' check (status in ('AVAILABLE','RESERVED','SOLD','UNVERIFIED')),
  region_code text references public.administrative_regions(code),
  address text,
  price_idr numeric(18,2),
  area_m2 numeric(18,2),
  source text,
  notes text,
  geometry extensions.geometry(MultiPolygon, 4326) not null,
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists spatial_assets_region_idx on public.spatial_assets(region_code);
create index if not exists spatial_assets_geometry_gix on public.spatial_assets using gist(geometry);
create index if not exists spatial_assets_created_by_idx on public.spatial_assets(created_by);

alter table public.administrative_regions enable row level security;
alter table public.spatial_assets enable row level security;

grant select on public.administrative_regions to authenticated;
grant select, insert, update, delete on public.spatial_assets to authenticated;

create policy "authenticated users can read administrative regions"
on public.administrative_regions for select to authenticated using (true);

create policy "users can read own spatial assets"
on public.spatial_assets for select to authenticated
using ((select auth.uid()) = created_by);

create policy "users can create own spatial assets"
on public.spatial_assets for insert to authenticated
with check ((select auth.uid()) = created_by);

create policy "users can update own spatial assets"
on public.spatial_assets for update to authenticated
using ((select auth.uid()) = created_by)
with check ((select auth.uid()) = created_by);

create policy "users can delete own spatial assets"
on public.spatial_assets for delete to authenticated
using ((select auth.uid()) = created_by);

-- Read helper: GeoJSON output is convenient for Leaflet.
create or replace function public.get_my_spatial_assets()
returns table (
  id uuid,
  asset_code text,
  title text,
  asset_type text,
  status text,
  region_code text,
  address text,
  price_idr numeric,
  area_m2 numeric,
  source text,
  notes text,
  geometry jsonb
)
language sql
security invoker
set search_path = ''
as $$
  select
    a.id, a.asset_code, a.title, a.asset_type, a.status, a.region_code,
    a.address, a.price_idr, a.area_m2, a.source, a.notes,
    extensions.st_asgeojson(a.geometry)::jsonb as geometry
  from public.spatial_assets a
  where a.created_by = (select auth.uid())
  order by a.created_at desc;
$$;

revoke all on function public.get_my_spatial_assets() from public, anon;
grant execute on function public.get_my_spatial_assets() to authenticated;

-- Save helper: accepts GeoJSON Polygon or MultiPolygon from Leaflet.
create or replace function public.save_spatial_asset(
  p_id uuid,
  p_asset_code text,
  p_title text,
  p_asset_type text,
  p_status text,
  p_region_code text,
  p_address text,
  p_price_idr numeric,
  p_source text,
  p_notes text,
  p_geometry jsonb
)
returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_id uuid;
  v_geom extensions.geometry;
  v_area numeric;
begin
  if auth.uid() is null then raise exception 'Authentication required'; end if;
  v_geom := extensions.st_setsrid(extensions.st_geomfromgeojson(p_geometry::text), 4326);
  if extensions.geometrytype(v_geom) not in ('POLYGON','MULTIPOLYGON') then raise exception 'Geometry must be Polygon or MultiPolygon'; end if;
  if not extensions.st_isvalid(v_geom) then raise exception 'Invalid polygon geometry'; end if;
  v_geom := extensions.st_multi(v_geom);
  v_area := extensions.st_area(v_geom::extensions.geography);

  if p_id is null then
    insert into public.spatial_assets(asset_code,title,asset_type,status,region_code,address,price_idr,area_m2,source,notes,geometry,created_by)
    values(p_asset_code,p_title,p_asset_type,p_status,p_region_code,p_address,p_price_idr,v_area,p_source,p_notes,v_geom,auth.uid())
    returning id into v_id;
  else
    update public.spatial_assets
    set asset_code=p_asset_code,title=p_title,asset_type=p_asset_type,status=p_status,
        region_code=p_region_code,address=p_address,price_idr=p_price_idr,area_m2=v_area,
        source=p_source,notes=p_notes,geometry=v_geom,updated_at=now()
    where id=p_id and created_by=auth.uid()
    returning id into v_id;
    if v_id is null then raise exception 'Asset not found or update not allowed'; end if;
  end if;
  return v_id;
end;
$$;

revoke all on function public.save_spatial_asset(uuid,text,text,text,text,text,text,numeric,text,text,jsonb) from public, anon;
grant execute on function public.save_spatial_asset(uuid,text,text,text,text,text,text,numeric,text,text,jsonb) to authenticated;
