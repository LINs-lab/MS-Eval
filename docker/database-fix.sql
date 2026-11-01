\set ON_ERROR_STOP on
ALTER TABLE email.sent_log DROP CONSTRAINT IF EXISTS sent_log_message_id_fkey;
ALTER TABLE email.sent_log ADD CONSTRAINT sent_log_message_id_fkey
  FOREIGN KEY (message_id) REFERENCES email.messages(id) ON DELETE CASCADE;
DO $$
BEGIN
  IF to_regclass('email.folders') IS NULL THEN
    RAISE EXCEPTION 'Missing benchmark fixture';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'email'
    AND tablename = 'folders' AND indexdef ILIKE 'CREATE UNIQUE INDEX%'
    AND indexdef LIKE '%(name)%') THEN
    RAISE EXCEPTION 'email.folders(name) unique index is missing';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_index WHERE NOT indisvalid OR NOT indisready) THEN
    RAISE EXCEPTION 'Database has invalid indexes';
  END IF;
END $$;
CREATE SCHEMA mse_runtime;
CREATE TABLE mse_runtime.ready (ready boolean NOT NULL);
INSERT INTO mse_runtime.ready VALUES (true);
