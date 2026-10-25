-- point-in-time database snapshot
-- Captured at: 2026-10-05T10:00:00Z
CREATE TABLE search_documents_primary (resource_id TEXT, display_name TEXT, email TEXT, source_resource_id TEXT, indexed_at TEXT);
INSERT INTO search_documents_primary VALUES ('search_9001','Elin Strand','elin.s.old@example.net','account_9001','2026-10-04T08:00:00Z');
INSERT INTO search_documents_primary VALUES ('search_9002','Elin Strand','e.strand.other@example.net','account_9902','2026-10-04T08:00:00Z');
INSERT INTO search_documents_primary VALUES ('search_9003','Elin Strandberg','elin.strandberg@example.net','account_9903','2026-10-04T08:00:00Z');
