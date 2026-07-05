import sqlite3
import threading
from typing import List, Dict, Any, Optional

class DictionaryDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self.init_db()

    def get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            import os
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def init_db(self):
        conn = self.get_conn()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL COLLATE NOCASE,
                    description TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dict_tags (
                    dict_id INTEGER NOT NULL,
                    tag TEXT NOT NULL COLLATE NOCASE,
                    FOREIGN KEY(dict_id) REFERENCES dictionary(id) ON DELETE CASCADE
                )
            """)
            # Indexes for faster sorting and searching
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dict_tags_id ON dict_tags(dict_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dict_tags_tag ON dict_tags(tag)")

    def add_word(self, word: str, description: str, tags: List[str]) -> int:
        conn = self.get_conn()
        with conn:
            cursor = conn.execute(
                "INSERT INTO dictionary (word, description) VALUES (?, ?)",
                (word.strip(), description.strip())
            )
            dict_id = cursor.lastrowid
            
            for tag in tags:
                t = tag.strip()
                if t:
                    conn.execute("INSERT INTO dict_tags (dict_id, tag) VALUES (?, ?)", (dict_id, t))
            return dict_id

    def update_word(self, dict_id: int, word: str, description: str, tags: List[str]) -> bool:
        conn = self.get_conn()
        with conn:
            cursor = conn.execute(
                "UPDATE dictionary SET word = ?, description = ? WHERE id = ?",
                (word.strip(), description.strip(), dict_id)
            )
            if cursor.rowcount == 0:
                return False
            
            # Re-create tags
            conn.execute("DELETE FROM dict_tags WHERE dict_id = ?", (dict_id,))
            for tag in tags:
                t = tag.strip()
                if t:
                    conn.execute("INSERT INTO dict_tags (dict_id, tag) VALUES (?, ?)", (dict_id, t))
            return True

    def delete_word(self, dict_id: int) -> bool:
        conn = self.get_conn()
        with conn:
            cursor = conn.execute("DELETE FROM dictionary WHERE id = ?", (dict_id,))
            return cursor.rowcount > 0

    def get_words(self, search: str = "", sort_dir: str = "asc") -> List[Dict[str, Any]]:
        conn = self.get_conn()
        query = "SELECT id, word, description, created_at FROM dictionary"
        params = []
        
        if search:
            search = search.strip()
            # If search contains tags like '#tag', handle it
            if search.startswith("#"):
                tag = search[1:]
                query = """
                    SELECT d.id, d.word, d.description, d.created_at 
                    FROM dictionary d
                    JOIN dict_tags t ON d.id = t.dict_id
                    WHERE t.tag LIKE ?
                """
                params.append(f"%{tag}%")
            else:
                query += " WHERE word LIKE ? OR description LIKE ?"
                params.extend([f"%{search}%", f"%{search}%"])
                
        # Sorting
        sort_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"
        query += f" ORDER BY word {sort_dir}"
        
        rows = conn.execute(query, params).fetchall()
        results = []
        
        # Batch fetch tags to avoid N+1 query problem if there are many entries,
        # but for simplicity, we can fetch all tags for the returned IDs.
        if not rows:
            return results
            
        dict_ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in dict_ids)
        tags_rows = conn.execute(f"SELECT dict_id, tag FROM dict_tags WHERE dict_id IN ({placeholders})", dict_ids).fetchall()
        
        tags_map = {did: [] for did in dict_ids}
        for tr in tags_rows:
            tags_map[tr["dict_id"]].append(tr["tag"])
            
        for row in rows:
            results.append({
                "id": row["id"],
                "word": row["word"],
                "description": row["description"],
                "created_at": row["created_at"],
                "tags": tags_map.get(row["id"], [])
            })
            
        return results

    def get_word(self, dict_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_conn()
        row = conn.execute("SELECT id, word, description, created_at FROM dictionary WHERE id = ?", (dict_id,)).fetchone()
        if not row:
            return None
            
        tags_rows = conn.execute("SELECT tag FROM dict_tags WHERE dict_id = ?", (dict_id,)).fetchall()
        tags = [t["tag"] for t in tags_rows]
        
        return {
            "id": row["id"],
            "word": row["word"],
            "description": row["description"],
            "created_at": row["created_at"],
            "tags": tags
        }
