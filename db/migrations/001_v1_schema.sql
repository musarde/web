-- ============================================================
-- Musarde v1 schema migration 001
-- Designed: 2026-05-04 (Week 1 Day 1)
-- See ../../build-log/decisions.md (entries dated 2026-05-04)
--     for the design reasoning behind every choice in this file.
-- ============================================================
--
-- Apply order: this file is idempotent only on the extension
-- statement; CREATE TABLE will fail if any table already exists.
-- For a fresh Neon dev branch, that's the intended behavior.
--
-- Rollback (run in this exact order to respect FK dependencies):
--
--   DROP TABLE IF EXISTS document_chunks;
--   DROP TABLE IF EXISTS document_artists;
--   DROP TABLE IF EXISTS document_objects;
--   DROP TABLE IF EXISTS documents;
--   DROP TABLE IF EXISTS object_artists;
--   DROP TABLE IF EXISTS image_embeddings;
--   DROP TABLE IF EXISTS images;
--   DROP TABLE IF EXISTS artists;
--   DROP TABLE IF EXISTS objects;
--   -- DROP EXTENSION IF EXISTS vector;  -- uncomment only if removing pgvector entirely
--
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- objects: artworks across all sources
-- ============================================================
CREATE TABLE objects (
  id                BIGSERIAL PRIMARY KEY,
  source            TEXT NOT NULL CHECK (source IN ('met', 'aic', 'getty', 'sam')),
  source_object_id  TEXT NOT NULL,

  title             TEXT,
  object_name       TEXT,
  object_number     TEXT,

  date_string       TEXT,
  date_start_year   INT,
  date_end_year     INT,

  department        TEXT,
  classification    TEXT,
  medium            TEXT,
  aat_type_uris     TEXT[] NOT NULL DEFAULT '{}',

  is_public_domain  BOOLEAN NOT NULL,
  is_highlight      BOOLEAN NOT NULL DEFAULT FALSE,
  is_on_view        BOOLEAN,

  iiif_manifest_url TEXT,

  raw_metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,

  ingested_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_updated_at TIMESTAMPTZ,

  UNIQUE (source, source_object_id)
);

CREATE INDEX objects_aat_type_uris_idx ON objects USING GIN (aat_type_uris);

-- ============================================================
-- images: assets, multiple per object possible
-- ============================================================
CREATE TABLE images (
  id              BIGSERIAL PRIMARY KEY,
  object_id       BIGINT NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  source_image_id TEXT NOT NULL,

  iiif_base_url   TEXT,
  fallback_url    TEXT,

  width           INT,
  height          INT,
  mime_type       TEXT,

  is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
  display_order   INT,

  license         TEXT NOT NULL CHECK (license IN ('cc0', 'cc-by-4.0', 'other')),
  license_uri     TEXT,

  raw_metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,

  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (object_id, source_image_id)
);

CREATE INDEX images_object_id_idx ON images(object_id);
CREATE UNIQUE INDEX images_primary_per_object
  ON images(object_id) WHERE is_primary;

-- ============================================================
-- image_embeddings: CLIP/SigLIP vectors (768-dim for OpenCLIP ViT-L/14)
-- ============================================================
CREATE TABLE image_embeddings (
  id            BIGSERIAL PRIMARY KEY,
  image_id      BIGINT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
  model_name    TEXT NOT NULL,                   -- 'openclip-vit-l-14' for v1
  model_version TEXT NOT NULL,                   -- 'laion2b_s32b_b82k' for v1
  embedding     vector(768) NOT NULL,
  computed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (image_id, model_name, model_version)
);

CREATE INDEX image_embeddings_hnsw_idx
  ON image_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX image_embeddings_image_id_idx ON image_embeddings(image_id);

-- ============================================================
-- artists: M:N attribution via object_artists
-- ============================================================
CREATE TABLE artists (
  id                BIGSERIAL PRIMARY KEY,
  source            TEXT NOT NULL CHECK (source IN ('met', 'aic', 'getty', 'sam')),
  source_artist_id  TEXT NOT NULL,

  name              TEXT NOT NULL,
  display_bio       TEXT,

  birth_year        INT,
  death_year        INT,

  nationality       TEXT,
  gender            TEXT,

  ulan_uri          TEXT,
  wikidata_uri      TEXT,

  raw_metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,

  ingested_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_updated_at TIMESTAMPTZ,

  UNIQUE (source, source_artist_id)
);

CREATE INDEX artists_ulan_uri_idx
  ON artists(ulan_uri) WHERE ulan_uri IS NOT NULL;
CREATE INDEX artists_wikidata_uri_idx
  ON artists(wikidata_uri) WHERE wikidata_uri IS NOT NULL;
CREATE INDEX artists_name_idx ON artists(name);

CREATE TABLE object_artists (
  id            BIGSERIAL PRIMARY KEY,
  object_id     BIGINT NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  artist_id     BIGINT NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
  role          TEXT,
  display_order INT,
  ingested_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE NULLS NOT DISTINCT (object_id, artist_id, role)
);

CREATE INDEX object_artists_object_id_idx ON object_artists(object_id);
CREATE INDEX object_artists_artist_id_idx ON object_artists(artist_id);

-- ============================================================
-- documents + chunks + join tables: text corpus for RAG
-- ============================================================
CREATE TABLE documents (
  id                 BIGSERIAL PRIMARY KEY,
  source             TEXT NOT NULL CHECK (source IN ('met', 'aic', 'getty', 'sam', 'curated')),
  source_document_id TEXT,

  document_type      TEXT NOT NULL CHECK (document_type IN (
                       'description', 'biography', 'tombstone', 'citation',
                       'exhibition_history', 'essay', 'interview', 'criticism',
                       'label'
                     )),

  title              TEXT,
  author             TEXT,

  content            TEXT NOT NULL,
  language           TEXT NOT NULL DEFAULT 'en',
  format             TEXT NOT NULL DEFAULT 'markdown'
                       CHECK (format IN ('markdown', 'plain', 'html')),

  published_at       DATE,
  source_url         TEXT,

  license            TEXT NOT NULL CHECK (license IN ('cc0', 'cc-by-4.0', 'other')),
  license_uri        TEXT,
  attribution        TEXT,

  raw_metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,

  ingested_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_updated_at  TIMESTAMPTZ,

  -- Museum sources (met/aic/getty/sam) must supply a natural key.
  -- Only 'curated' content is allowed to omit source_document_id.
  CHECK (source = 'curated' OR source_document_id IS NOT NULL)
);

CREATE UNIQUE INDEX documents_source_natural_key_idx
  ON documents(source, source_document_id)
  WHERE source_document_id IS NOT NULL;
CREATE INDEX documents_document_type_idx ON documents(document_type);
CREATE INDEX documents_source_idx ON documents(source);

CREATE TABLE document_objects (
  id          BIGSERIAL PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  object_id   BIGINT NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (document_id, object_id)
);

CREATE INDEX document_objects_object_id_idx ON document_objects(object_id);
CREATE INDEX document_objects_document_id_idx ON document_objects(document_id);

CREATE TABLE document_artists (
  id          BIGSERIAL PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  artist_id   BIGINT NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (document_id, artist_id)
);

CREATE INDEX document_artists_artist_id_idx ON document_artists(artist_id);
CREATE INDEX document_artists_document_id_idx ON document_artists(document_id);

CREATE TABLE document_chunks (
  id           BIGSERIAL PRIMARY KEY,
  document_id  BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index  INT NOT NULL,
  content      TEXT NOT NULL,
  start_offset INT,
  end_offset   INT,
  -- Deliberately no ingested_at: chunks are derived from a single parent
  -- document, not an M:N junction. Re-chunking (e.g. on chunking-parameter
  -- change) is atomic: DELETE all + INSERT all for the document in one
  -- transaction. Per-chunk freshness has no semantic meaning beyond what
  -- the parent document's ingested_at / last_seen_at already provide.
  UNIQUE (document_id, chunk_index)
);

CREATE INDEX document_chunks_document_id_idx ON document_chunks(document_id);

-- ============================================================
-- Deferred (Week 1 text-embedding bake-off blocks this):
--   document_chunk_embeddings — same shape as image_embeddings,
--   vector(N) dimension fills in when bake-off picks a winner.
-- ============================================================
