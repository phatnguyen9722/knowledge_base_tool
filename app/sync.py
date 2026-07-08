import os
import shutil
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
import datetime
import tempfile

from app.config import Settings

def get_sync_config(settings: Settings) -> dict:
    return {"sync_dir": "/sync", "backup_dir": "/backup"}

def set_sync_config(settings: Settings, sync_dir: str, backup_dir: str = ""):
    pass # Managed by Docker and setup script

def _get_category_dirs(settings: Settings, sync_dir: Path) -> Dict[str, tuple[Path, Path]]:
    return {
        "notes": (settings.notes_dir, sync_dir / "notes"),
        "posts": (settings.posts_dir, sync_dir / "posts"),
        "tasks": (settings.tasks_dir, sync_dir / "tasks"),
        "vault": (settings.vault_dir, sync_dir / "vault"),
    }

def get_sync_preview(settings: Settings) -> List[dict]:
    config = get_sync_config(settings)
    sync_dir_str = config.get("sync_dir", "")
    if not sync_dir_str:
        raise ValueError("Sync folder is not configured.")
    
    sync_dir = Path(sync_dir_str)
    categories = _get_category_dirs(settings, sync_dir)
    diffs = []

    for cat, (local_dir, remote_dir) in categories.items():
        if not local_dir.exists():
            continue
            
        local_files = {p.relative_to(local_dir): p for p in local_dir.rglob("*") if p.is_file()}
        remote_files = {p.relative_to(remote_dir): p for p in remote_dir.rglob("*") if p.is_file()} if remote_dir.exists() else {}

        all_rel_paths = set(local_files.keys()) | set(remote_files.keys())
        
        for rel_path in sorted(all_rel_paths):
            # Skip hidden files
            if str(rel_path).startswith('.') or '/.' in str(rel_path):
                continue

            lf = local_files.get(rel_path)
            rf = remote_files.get(rel_path)
            
            if lf and rf:
                l_mtime = lf.stat().st_mtime
                r_mtime = rf.stat().st_mtime
                # 2 seconds tolerance for cross-filesystem precision
                if abs(l_mtime - r_mtime) > 2.0:
                    if l_mtime > r_mtime:
                        diffs.append({
                            "rel_path": str(rel_path), "category": cat,
                            "action": "push", "reason": "newer locally",
                            "local_mtime": l_mtime, "remote_mtime": r_mtime
                        })
                    else:
                        diffs.append({
                            "rel_path": str(rel_path), "category": cat,
                            "action": "pull", "reason": "newer remotely",
                            "local_mtime": l_mtime, "remote_mtime": r_mtime
                        })
            elif lf and not rf:
                diffs.append({
                    "rel_path": str(rel_path), "category": cat,
                    "action": "push", "reason": "missing remotely",
                    "local_mtime": lf.stat().st_mtime, "remote_mtime": 0
                })
            elif rf and not lf:
                diffs.append({
                    "rel_path": str(rel_path), "category": cat,
                    "action": "pull", "reason": "missing locally",
                    "local_mtime": 0, "remote_mtime": rf.stat().st_mtime
                })
                
    return diffs

def execute_sync(settings: Settings) -> dict:
    try:
        diffs = get_sync_preview(settings)
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    config = get_sync_config(settings)
    sync_dir_str = config.get("sync_dir", "")
    if not sync_dir_str:
        return {"status": "error", "message": "Not configured"}
        
    sync_dir = Path(sync_dir_str)
    categories = _get_category_dirs(settings, sync_dir)
    
    pushed = 0
    pulled = 0
    
    for diff in diffs:
        cat = diff["category"]
        rel_path = diff["rel_path"]
        action = diff["action"]
        
        local_dir, remote_dir = categories[cat]
        lf = local_dir / rel_path
        rf = remote_dir / rel_path
        
        if action == "push":
            rf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(lf, rf)
            pushed += 1
        elif action == "pull":
            lf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rf, lf)
            pulled += 1
            
    return {"status": "success", "pushed": pushed, "pulled": pulled}

def execute_initial_setup(settings: Settings) -> dict:
    config = get_sync_config(settings)
    sync_dir_str = config.get("sync_dir", "")
    if not sync_dir_str:
        return {"status": "error", "message": "Sync folder is not configured."}
        
    sync_dir = Path(sync_dir_str)
    categories = _get_category_dirs(settings, sync_dir)
    pushed = 0
    
    for cat, (local_dir, remote_dir) in categories.items():
        if not local_dir.exists():
            continue
        
        for p in local_dir.rglob("*"):
            if p.is_file() and not (p.name.startswith('.') or '/.' in str(p)):
                rel_path = p.relative_to(local_dir)
                rf = remote_dir / rel_path
                rf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, rf)
                pushed += 1
                
    return {"status": "success", "pushed": pushed}

def execute_backup(settings: Settings) -> dict:
    config = get_sync_config(settings)
    backup_dir_str = config.get("backup_dir", "")
    if not backup_dir_str:
        return {"status": "error", "message": "Backup folder is not configured."}
        
    backup_dir = Path(backup_dir_str)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"kb_backup_{timestamp}"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for cat, (local_dir, _) in _get_category_dirs(settings, backup_dir).items():
            if local_dir.exists():
                shutil.copytree(local_dir, tmp_path / cat)
                
        zip_path = backup_dir / zip_name
        shutil.make_archive(str(zip_path), 'zip', tmp_dir)
        
    return {"status": "success", "file": f"{zip_name}.zip"}
