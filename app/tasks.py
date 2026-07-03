"""Task Manager — Task tracking with version history.

Each task is stored in its own directory within ``tasks/``. Updates generate new 
files following the pattern `dd_mm_yyyy_user_name_updated_times.md` to preserve 
history.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import frontmatter
from slugify import slugify

__all__ = ["SubTask", "TaskVersion", "Task", "TaskManager"]


@dataclass
class SubTask:
    title: str
    status: str  # "to-do", "in-progress", "done"

    def to_dict(self):
        return {"title": self.title, "status": self.status}


@dataclass
class TaskVersion:
    filename: str
    version: int
    user: str
    date_str: str  # dd_mm_yyyy
    title: str
    content: str
    subtasks: list[SubTask]
    created: str
    updated: str


@dataclass
class Task:
    slug: str
    latest: TaskVersion
    history: list[TaskVersion] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.latest.title


class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def _task_dir(self, slug: str) -> Path:
        return self.tasks_dir / slug

    def _unique_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "task"
        slug, n = base, 2
        while self._task_dir(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def _parse_filename(self, filename: str) -> tuple[str, str, int]:
        """Parses `dd_mm_yyyy_user_name_updated_times.md`.
        Returns (date_str, user_name, version).
        """
        stem = Path(filename).stem
        # e.g., 03_07_2026_kaiser_updated_1
        # Try to split by '_updated_'
        if "_updated_" in stem:
            prefix, ver_str = stem.rsplit("_updated_", 1)
            try:
                version = int(ver_str)
            except ValueError:
                version = 0
            
            # prefix is like "03_07_2026_kaiser"
            # Date is strictly 10 chars "DD_MM_YYYY"
            if len(prefix) > 11 and prefix[:10].count("_") == 2:
                date_str = prefix[:10]
                user = prefix[11:]
            else:
                date_str = ""
                user = prefix
            return date_str, user, version
        return "", stem, 0

    def _generate_filename(self, user: str, version: int) -> str:
        date_str = datetime.now().strftime("%d_%m_%Y")
        safe_user = slugify(user) or "unknown"
        return f"{date_str}_{safe_user}_updated_{version}.md"

    def _read_version(self, path: Path) -> TaskVersion | None:
        if not path.exists():
            return None
        fm = frontmatter.load(str(path))
        m = fm.metadata or {}
        
        date_str, user_name, version = self._parse_filename(path.name)
        
        # Override with frontmatter if available, otherwise fallback to filename parsing
        user = str(m.get("user", user_name))
        
        subtasks_data = m.get("subtasks", [])
        subtasks = []
        for st in subtasks_data:
            if isinstance(st, dict):
                subtasks.append(SubTask(
                    title=str(st.get("title", "")),
                    status=str(st.get("status", "to-do"))
                ))
        
        return TaskVersion(
            filename=path.name,
            version=m.get("version", version),
            user=user,
            date_str=date_str,
            title=str(m.get("title", "Untitled")),
            content=fm.content,
            subtasks=subtasks,
            created=str(m.get("created", "")),
            updated=str(m.get("updated", ""))
        )

    def _write_version(self, tdir: Path, version: TaskVersion) -> None:
        tdir.mkdir(parents=True, exist_ok=True)
        meta = {
            "title": version.title,
            "user": version.user,
            "version": version.version,
            "created": version.created,
            "updated": version.updated,
            "subtasks": [st.to_dict() for st in version.subtasks]
        }
        fm = frontmatter.Post(version.content, **meta)
        path = tdir / version.filename
        path.write_text(frontmatter.dumps(fm), encoding="utf-8")

    def create(self, data: dict) -> str:
        title = (data.get("title") or "Untitled").strip()
        slug = self._unique_slug(title)
        user = (data.get("user") or "unknown").strip()
        
        subtasks_raw = data.get("subtasks", [])
        subtasks = []
        for st in subtasks_raw:
            subtasks.append(SubTask(title=st.get("title", "").strip(), status=st.get("status", "to-do")))
        
        tdir = self._task_dir(slug)
        filename = self._generate_filename(user, 0)
        
        today = date.today().isoformat()
        
        tv = TaskVersion(
            filename=filename,
            version=0,
            user=user,
            date_str=datetime.now().strftime("%d_%m_%Y"),
            title=title,
            content=data.get("content", ""),
            subtasks=subtasks,
            created=today,
            updated=today
        )
        
        self._write_version(tdir, tv)
        return slug

    def update(self, slug: str, data: dict) -> str | None:
        task = self.read(slug)
        if not task:
            return None
        
        latest = task.latest
        new_version_num = latest.version + 1
        
        user = (data.get("user") or latest.user).strip()
        title = (data.get("title") or latest.title).strip()
        content = data.get("content", latest.content)
        
        if "subtasks" in data:
            subtasks = []
            for st in data["subtasks"]:
                subtasks.append(SubTask(title=st.get("title", "").strip(), status=st.get("status", "to-do")))
        else:
            subtasks = latest.subtasks
            
        filename = self._generate_filename(user, new_version_num)
        
        tv = TaskVersion(
            filename=filename,
            version=new_version_num,
            user=user,
            date_str=datetime.now().strftime("%d_%m_%Y"),
            title=title,
            content=content,
            subtasks=subtasks,
            created=latest.created,
            updated=date.today().isoformat()
        )
        
        self._write_version(self._task_dir(slug), tv)
        return slug

    def read(self, slug: str) -> Task | None:
        tdir = self._task_dir(slug)
        if not tdir.exists() or not tdir.is_dir():
            return None
        
        versions = []
        for f in tdir.glob("*.md"):
            tv = self._read_version(f)
            if tv:
                versions.append(tv)
        
        if not versions:
            return None
            
        # Sort by version number descending
        versions.sort(key=lambda v: v.version, reverse=True)
        
        return Task(
            slug=slug,
            latest=versions[0],
            history=versions[1:]
        )

    def read_version(self, slug: str, version_num: int) -> TaskVersion | None:
        task = self.read(slug)
        if not task:
            return None
        if task.latest.version == version_num:
            return task.latest
        for v in task.history:
            if v.version == version_num:
                return v
        return None

    def delete_version(self, slug: str, version_num: int) -> bool:
        task = self.read(slug)
        if not task:
            return False
            
        v_to_delete = self.read_version(slug, version_num)
        if not v_to_delete:
            return False
            
        path = self._task_dir(slug) / v_to_delete.filename
        if path.exists():
            path.unlink()
            
        # If no files left, delete directory
        tdir = self._task_dir(slug)
        if not any(tdir.iterdir()):
            tdir.rmdir()
            
        return True

    def delete(self, slug: str) -> bool:
        tdir = self._task_dir(slug)
        if not tdir.exists():
            return False
        for f in tdir.glob("*"):
            f.unlink()
        tdir.rmdir()
        return True

    def list(self, q: str = "") -> list[Task]:
        tasks = []
        for d in self.tasks_dir.iterdir():
            if d.is_dir():
                t = self.read(d.name)
                if t:
                    tasks.append(t)
        
        if q:
            ql = q.strip().lower()
            filtered = []
            for t in tasks:
                if (ql in t.latest.title.lower() or 
                    ql in t.latest.content.lower() or 
                    ql in t.latest.user.lower()):
                    filtered.append(t)
            tasks = filtered
            
        # Sort by latest update descending
        tasks.sort(key=lambda t: t.latest.updated, reverse=True)
        return tasks
