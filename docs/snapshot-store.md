# FirmaBlick Issue #9: append-only raw snapshots and acquisition vintages

## Preflight and deployment boundary
- Linked GitHub account has push/admin access. Issue #8 is merged into the prototype branch; Python and Node CI are available.
- The connected Supabase account currently contains an IIA project only. There is no dedicated FirmaBlick project; NO Supabase database/storage configuration or access to IIA is allowed.
- A local, standard-library SQLite + filesystem implementation is the reference implementation for CI. Production hosted storage requires a separately approved isolated FirmaBlick project.
- GENESIS live authentication is optional and requires a protected personal token. Offline CI uses non-sensitive synthetic official-format fixtures.

## Data architecture
SnapshotStore(root) uses root/firmablick/v1 as a reserved namespace. Files are named by SHA-256 under objects/<first-two-hex>/<next-two-hex>/<full-digest>. All raw bytes are preserved. New blobs use temporary files, fsync and atomic hard-link creation to prevent overwrites. Existing hashes are checked byte-for-byte; tampered bytes block reads and acquisitions.

SQLite tables: object_blobs (hash, length, storage key, first-seen UTC), acquisitions (UUID, dataset, retrieved UTC, source URI, safe query, HTTP response metadata, full inventory, optional source release time and permanently false publication flag), acquisition_objects (two roles per retrieval, foreign-key-linked hashes). Indices support dataset+UTC as-of queries. Triggers refuse UPDATE and DELETE on all three tables; publication_approved has a database CHECK constraint equal to zero. Every acquisition gets its own UUID, including identical responses. Identical blobs are deduplicated. Revised blobs and earlier retrieval events remain accessible.

All query parameters are allowlisted to exclude credentials. Only HTTP status, Content-Type, ETag and Last-Modified are stored. Root and object directories are chmod 0700, files/database 0600. Symlink checks block obvious root/blob redirection. Integrity is reverified on reads, not assumed. Failed metadata transactions cannot create published acquisition events. Orphaned unreferenced source blobs may remain after a failed transaction; they are not publicly accessible.

## Testing and operation
- python3 -m unittest discover -s tests -p 'test_*.py' -v
- npm ci && npm run build && npm test
- GENESIS_TOKEN set securely: python3 -m ingestion.genesis fetch --startyear 2021 --endyear 2026 --output artifacts/genesis
- In the command above, artifacts/genesis is a parent archive root. Source bytes and SQLite state live in artifacts/genesis/firmablick/v1. This parent is excluded by .gitignore.

The tests cover byte-preserving SHA-256, retrieval metadata, deduplication, distinct acquisition events, revised historical vintages, as-of queries, same-second boundaries, corruption, forbidden update/delete/publication, failure-injected blob writes and SQLite transactions, local storage permissions, namespace isolation, credential minimization and Issue #8 integration.

## Limits and future hosted implementation
SQLite is a reference persistence implementation, not an authenticated multi-user production service. Filesystem ownership can be bypassed by processes under the same OS account or by administrators. These are append-only application and SQL guarantees, not WORM/compliance-grade object lock or a signed audit trail. Multi-host durability, disaster recovery and production backup are deferred.

Once a dedicated FirmaBlick Supabase project is explicitly configured, adapt the three-table schema into a private PostgreSQL schema, revoke access to anon/authenticated, and create a private bucket with non-upsert writes under digest keys. Keep privileged ingestion entirely server-side. Test actual RLS, object-storage permissions, integrity, revision replay and recovery before activation. Do not use IIA's existing project or keys.

Reference: GitHub issues #5, #7, #8 and #9; docs/source-registry.md and docs/genesis-ingestion.md.
