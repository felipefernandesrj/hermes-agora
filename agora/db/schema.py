"""Ágora SQLite schema (shared)."""

SCHEMA_SQL = """
            CREATE TABLE IF NOT EXISTS agora_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agora_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                linked_task_id TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at INTEGER NOT NULL,
                FOREIGN KEY (channel_id) REFERENCES agora_channels(id)
            );

            CREATE INDEX IF NOT EXISTS idx_threads_channel ON agora_threads(channel_id);
            CREATE INDEX IF NOT EXISTS idx_threads_task ON agora_threads(linked_task_id);

            CREATE TABLE IF NOT EXISTS agora_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                thread_id INTEGER,
                author_type TEXT NOT NULL,
                author_profile TEXT,
                body TEXT NOT NULL,
                linked_task_id TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (channel_id) REFERENCES agora_channels(id),
                FOREIGN KEY (thread_id) REFERENCES agora_threads(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_channel ON agora_messages(channel_id);
            CREATE INDEX IF NOT EXISTS idx_messages_thread ON agora_messages(thread_id);
            CREATE INDEX IF NOT EXISTS idx_messages_task ON agora_messages(linked_task_id);

            CREATE TABLE IF NOT EXISTS agora_agent_status (
                profile TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                current_task_id TEXT,
                current_step TEXT,
                status_text TEXT,
                last_heartbeat_at INTEGER NOT NULL,
                pid INTEGER,
                run_id INTEGER,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS agora_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                proposal TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT,
                decided_by TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES agora_threads(id)
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_thread ON agora_decisions(thread_id);

            CREATE TABLE IF NOT EXISTS agora_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT,
                created_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_entity ON agora_events(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_events_created ON agora_events(created_at);

            CREATE TABLE IF NOT EXISTS agora_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                body_snippet TEXT,
                author_profile TEXT,
                read_at INTEGER,
                ack_at INTEGER,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (message_id) REFERENCES agora_messages(id),
                FOREIGN KEY (channel_id) REFERENCES agora_channels(id)
            );

            CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON agora_notifications(recipient);
            CREATE INDEX IF NOT EXISTS idx_notifications_recipient_created ON agora_notifications(recipient, created_at);
            CREATE INDEX IF NOT EXISTS idx_notifications_recipient_read ON agora_notifications(recipient, read_at);

            CREATE TABLE IF NOT EXISTS agora_migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL,
                source_table TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                target_id INTEGER,
                migrated_at INTEGER NOT NULL,
                UNIQUE(source_path, source_table, source_id)
            );

            CREATE INDEX IF NOT EXISTS idx_migration_log_source ON agora_migration_log(source_path, source_table, source_id);
            """
