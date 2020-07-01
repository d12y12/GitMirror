-- github Database
PRAGMA foreign_keys = off;
BEGIN TRANSACTION;
-- Table: Configurations
DROP TABLE IF EXISTS Configurations;
CREATE TABLE Configurations (
  service_name TEXT UNIQUE PRIMARY KEY NOT NULL,
  host TEXT NOT NULL,
  consistency INTEGER NOT NULL DEFAULT (0),
  crontab TEXT NOT NULL,
  repositories TEXT NOT NULL,
  original_sql TEXT
);
INSERT INTO
  Configurations (
    service_name,
    host,
    consistency,
    crontab,
    repositories,
    original_sql
  )
VALUES
  (
    'github',
    '192.168.0.108:8090',
    1,
    '*/5 * * * *',
    '{"cgit": [], "github": [{"source": "d12y12", "excludes": [], "targets": []}], "gitee": []}',
    ''
  );
-- Table: Repositories
DROP TABLE IF EXISTS Repositories;
CREATE TABLE Repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    section TEXT,
    owner TEXT,
    descriptions TEXT,
    html_url TEXT NOT NULL,
    clone_url TEXT UNIQUE NOT NULL,
    target_url TEXT,
    source TEXT NOT NULL,
    source_type TEXT,
    last_check DATETIME NOT NULL,
    last_update DATETIME
  );
COMMIT TRANSACTION;
PRAGMA foreign_keys = on;