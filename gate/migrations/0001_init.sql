CREATE TABLE IF NOT EXISTS members (
  email TEXT PRIMARY KEY,
  invite_code TEXT,
  joined_at TEXT NOT NULL,
  last_seen TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invites (
  code TEXT PRIMARY KEY,
  note TEXT,
  created_at TEXT NOT NULL,
  used_by TEXT,
  used_at TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS comments (
  id TEXT PRIMARY KEY,
  page TEXT NOT NULL,
  parent_id TEXT,
  quote TEXT,
  prefix TEXT,
  suffix TEXT,
  body TEXT NOT NULL,
  author TEXT NOT NULL,
  created_at TEXT NOT NULL,
  resolved INTEGER NOT NULL DEFAULT 0,
  deleted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS comments_page ON comments(page);
CREATE TABLE IF NOT EXISTS views (
  email TEXT NOT NULL,
  path TEXT NOT NULL,
  at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS views_at ON views(at);
