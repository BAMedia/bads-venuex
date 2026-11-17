CREATE TABLE IF NOT EXISTS subscribers (
  email TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  source TEXT,
  consent INTEGER NOT NULL DEFAULT 1 CHECK (consent = 1)
);
