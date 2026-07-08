import os
from pathlib import Path
from typing import Any

from .config import load_settings

class VaultManager:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.vault_dir = self.settings.vault_dir
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, rel_path: str) -> Path:
        """Ensure the path doesn't escape the vault directory."""
        # Strip leading slashes to make it truly relative
        rel_path = rel_path.lstrip("/")
        if not rel_path:
            return self.vault_dir
        
        target = (self.vault_dir / rel_path).resolve()
        if not str(target).startswith(str(self.vault_dir.resolve())):
            raise ValueError("Path escaping vault directory is not allowed.")
        return target

    def get_file_tree(self) -> dict[str, Any]:
        """Recursively build a tree of folders and .md files."""
        def build_tree(current_dir: Path) -> dict[str, Any]:
            tree: dict[str, Any] = {
                "name": current_dir.name if current_dir != self.vault_dir else "Vault",
                "path": str(current_dir.relative_to(self.vault_dir)) if current_dir != self.vault_dir else "",
                "type": "folder",
                "children": []
            }
            
            try:
                # Sort folders first, then files
                entries = sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                for entry in entries:
                    if entry.name.startswith("."):
                        continue
                    if entry.is_dir():
                        tree["children"].append(build_tree(entry))
                    elif entry.is_file() and entry.suffix.lower() == ".md":
                        tree["children"].append({
                            "name": entry.name,
                            "path": str(entry.relative_to(self.vault_dir)),
                            "type": "file"
                        })
            except PermissionError:
                pass
                
            return tree

        return build_tree(self.vault_dir)

    def read_file(self, rel_path: str) -> str:
        """Read the content of a markdown file."""
        target = self._safe_path(rel_path)
        if not target.exists() or not target.is_file():
            return ""
        return target.read_text(encoding="utf-8")

    def write_file(self, rel_path: str, content: str) -> None:
        """Write content to a markdown file."""
        target = self._safe_path(rel_path)
        # Ensure parent directories exist
        target.parent.mkdir(parents=True, exist_ok=True)
        # Force .md extension if missing
        if target.suffix.lower() != ".md":
            target = target.with_suffix(".md")
        target.write_text(content, encoding="utf-8")

    def create_node(self, rel_path: str, is_dir: bool = False) -> None:
        """Create a new file or folder."""
        target = self._safe_path(rel_path)
        
        if is_dir:
            if target.exists():
                raise ValueError("Folder already exists.")
            target.mkdir(parents=True, exist_ok=True)
        else:
            if target.suffix.lower() != ".md":
                target = target.with_suffix(".md")
            if target.exists():
                raise ValueError("File already exists.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# New Note\n", encoding="utf-8")

    def delete_node(self, rel_path: str) -> None:
        """Delete a file or folder."""
        target = self._safe_path(rel_path)
        if not target.exists() or target == self.vault_dir:
            return
            
        if target.is_dir():
            import shutil
            shutil.rmtree(target)
        else:
            target.unlink()

    def rename_node(self, old_rel_path: str, new_rel_path: str) -> None:
        """Rename a file or folder."""
        old_target = self._safe_path(old_rel_path)
        new_target = self._safe_path(new_rel_path)
        
        if not old_target.exists() or old_target == self.vault_dir:
            return
            
        if old_target.is_file() and new_target.suffix.lower() != ".md":
            new_target = new_target.with_suffix(".md")
            
        # Ensure parent exists
        new_target.parent.mkdir(parents=True, exist_ok=True)
        old_target.rename(new_target)

# Singleton instance
vault_manager = VaultManager()
