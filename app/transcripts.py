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

    def _extract_text(self, event: dict) -> str:
        text = ""
        ev_type = event.get("type")
        msg = event.get("message", {})
        
        if ev_type == "user":
            content = msg.get("content")
            if isinstance(content, str):
                text += content
            elif isinstance(content, list):
                for c in content:
                    if c.get("type") == "tool_result" and c.get("content"):
                        text += str(c.get("content", ""))
        elif ev_type == "assistant":
            content = msg.get("content")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "text" and c.get("text"):
                        text += c.get("text", "")
                    elif c.get("type") == "thinking" and c.get("thinking"):
                        text += c.get("thinking", "")
                    elif c.get("type") == "tool_use" and c.get("input"):
                        text += json.dumps(c.get("input", {}))
        return text

    def search(self, query: str) -> list[dict]:
        query_lower = query.lower()
        results = []
        
        for coll_dir in self.data_dir.iterdir():
            if not coll_dir.is_dir():
                continue
                
            for file_path in coll_dir.glob("*.jsonl"):
                slug = file_path.stem
                name = slug
                matched = False
                snippet = ""
                
                with file_path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if data.get("type") == "ai-title" and "aiTitle" in data:
                                name = data["aiTitle"]
                            
                            if not matched:
                                raw_text = self._extract_text(data)
                                if query_lower in raw_text.lower():
                                    matched = True
                                    # Generate snippet
                                    idx = raw_text.lower().find(query_lower)
                                    start = max(0, idx - 80)
                                    end = min(len(raw_text), idx + len(query) + 80)
                                    snip = raw_text[start:end]
                                    
                                    import html
                                    snip_esc = html.escape(snip)
                                    query_esc = html.escape(query)
                                    query_esc_lower = query_esc.lower()
                                    
                                    # Highlight query
                                    snip_lower = snip_esc.lower()
                                    q_idx = snip_lower.find(query_esc_lower)
                                    if q_idx != -1:
                                        snip_esc = snip_esc[:q_idx] + "<mark>" + snip_esc[q_idx:q_idx+len(query_esc)] + "</mark>" + snip_esc[q_idx+len(query_esc):]
                                        
                                    snippet = ("..." if start > 0 else "") + snip_esc + ("..." if end < len(raw_text) else "")
                        except json.JSONDecodeError:
                            pass
                            
                if matched:
                    results.append({
                        "coll_slug": coll_dir.name,
                        "slug": slug,
                        "name": name,
                        "snippet": snippet
                    })
                    
        return results
