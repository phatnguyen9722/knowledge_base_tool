import json
import datetime
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from slugify import slugify

@dataclass
class Transcript:
    coll_slug: str
    slug: str
    session_id: str
    name: str
    created_at: str
    events: list[dict] = field(default_factory=list)

class TranscriptManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_files()
        
    def _migrate_legacy_files(self):
        """Moves any .jsonl files in the root dir to a 'default' collection."""
        root_files = list(self.data_dir.glob("*.jsonl"))
        if root_files:
            default_dir = self.data_dir / "default"
            default_dir.mkdir(exist_ok=True)
            for f in root_files:
                shutil.move(str(f), str(default_dir / f.name))

    def _safe_filename(self, slug: str) -> str:
        return f"{slug}.jsonl"
        
    def import_transcript(self, coll_slug: str, name: str, content: str) -> str:
        coll_dir = self.data_dir / coll_slug
        coll_dir.mkdir(parents=True, exist_ok=True)
        
        base_slug = slugify(name) or "transcript"
        slug = base_slug
        counter = 1
        while (coll_dir / self._safe_filename(slug)).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        file_path = coll_dir / self._safe_filename(slug)
        file_path.write_text(content, encoding="utf-8")
        return slug

    def list_collections(self) -> list[dict]:
        collections = []
        for d in self.data_dir.iterdir():
            if d.is_dir():
                count = len(list(d.glob("*.jsonl")))
                if count > 0:
                    collections.append({"slug": d.name, "name": d.name.replace("-", " ").title(), "count": count})
        collections.sort(key=lambda c: c["name"])
        return collections

    def list_transcripts(self, coll_slug: str) -> list[Transcript]:
        coll_dir = self.data_dir / coll_slug
        if not coll_dir.exists() or not coll_dir.is_dir():
            return []
            
        transcripts = []
        for file in coll_dir.glob("*.jsonl"):
            slug = file.stem
            stats = file.stat()
            created_at = datetime.datetime.fromtimestamp(stats.st_ctime).isoformat()
            
            session_id = "unknown"
            name = slug
            with file.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "ai-title" and "aiTitle" in data:
                            name = data["aiTitle"]
                        if "sessionId" in data and session_id == "unknown":
                            session_id = data["sessionId"]
                    except json.JSONDecodeError:
                        pass
            transcripts.append(Transcript(coll_slug=coll_slug, slug=slug, session_id=session_id, name=name, created_at=created_at))
        transcripts.sort(key=lambda t: t.created_at, reverse=True)
        return transcripts

    def read(self, coll_slug: str, slug: str) -> Transcript | None:
        file_path = self.data_dir / coll_slug / self._safe_filename(slug)
        if not file_path.exists():
            return None
            
        events = []
        session_id = "unknown"
        name = slug
        created_at = datetime.datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
        
        with file_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    events.append(data)
                    if data.get("type") == "ai-title" and "aiTitle" in data:
                        name = data["aiTitle"]
                    if "sessionId" in data and session_id == "unknown":
                        session_id = data["sessionId"]
                except json.JSONDecodeError:
                    pass
                    
        return Transcript(coll_slug=coll_slug, slug=slug, session_id=session_id, name=name, created_at=created_at, events=events)

    def delete(self, coll_slug: str, slug: str) -> bool:
        file_path = self.data_dir / coll_slug / self._safe_filename(slug)
        if file_path.exists():
            file_path.unlink()
            
            # Clean up collection if empty
            coll_dir = self.data_dir / coll_slug
            if not list(coll_dir.glob("*.jsonl")):
                coll_dir.rmdir()
                
            return True
        return False
