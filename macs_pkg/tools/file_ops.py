"""File operations tool for MACS."""

from typing import Any, Dict, List, Optional
import os
import json
from pathlib import Path
import asyncio


class FileOpsTool:
    """Tool for file operations.

    Supports:
    - Reading files (text, JSON)
    - Writing files (text, JSON)
    - Listing directories
    - File metadata
    - Path operations
    """

    def __init__(self, base_path: Optional[str] = None):
        """Initialize file ops tool.

        Args:
            base_path: Base directory for file operations.
                     If None, uses current working directory.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base_path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_path / p

    async def read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read a file.

        Args:
            path: File path.
            encoding: Text encoding.

        Returns:
            Dictionary with file content or error.
        """
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return {
                    "path": str(path),
                    "error": f"File not found: {path}",
                    "success": False,
                }

            if not file_path.is_file():
                return {
                    "path": str(path),
                    "error": f"Not a file: {path}",
                    "success": False,
                }

            content = file_path.read_text(encoding=encoding)

            return {
                "path": str(path),
                "content": content,
                "size": file_path.stat().st_size,
                "success": True,
            }

        except Exception as e:
            return {
                "path": str(path),
                "error": str(e),
                "success": False,
            }

    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        """Write content to a file.

        Args:
            path: File path.
            content: Content to write.
            encoding: Text encoding.

        Returns:
            Dictionary with result or error.
        """
        try:
            file_path = self._resolve_path(path)

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content, encoding=encoding)

            return {
                "path": str(path),
                "bytes_written": len(content.encode(encoding)),
                "success": True,
            }

        except Exception as e:
            return {
                "path": str(path),
                "error": str(e),
                "success": False,
            }

    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read and parse a JSON file.

        Args:
            path: File path.

        Returns:
            Dictionary with parsed JSON or error.
        """
        try:
            result = await self.read_file(path)
            if not result["success"]:
                return result

            data = json.loads(result["content"])

            return {
                "path": str(path),
                "data": data,
                "success": True,
            }

        except json.JSONDecodeError as e:
            return {
                "path": str(path),
                "error": f"JSON parse error: {e}",
                "success": False,
            }
        except Exception as e:
            return {
                "path": str(path),
                "error": str(e),
                "success": False,
            }

    async def write_json(
        self,
        path: str,
        data: Any,
        indent: int = 2,
    ) -> Dict[str, Any]:
        """Write data to a JSON file.

        Args:
            path: File path.
            data: Data to serialize as JSON.
            indent: JSON indentation.

        Returns:
            Dictionary with result or error.
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            return await self.write_file(path, content)

        except Exception as e:
            return {
                "path": str(path),
                "error": str(e),
                "success": False,
            }

    async def list_directory(
        self,
        path: str = ".",
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """List directory contents.

        Args:
            path: Directory path.
            include_hidden: Include hidden files.

        Returns:
            Dictionary with directory listing or error.
        """
        try:
            dir_path = self._resolve_path(path)

            if not dir_path.exists():
                return {
                    "path": str(path),
                    "error": f"Directory not found: {path}",
                    "success": False,
                }

            if not dir_path.is_dir():
                return {
                    "path": str(path),
                    "error": f"Not a directory: {path}",
                    "success": False,
                }

            entries = []
            for entry in dir_path.iterdir():
                if not include_hidden and entry.name.startswith("."):
                    continue

                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": stat.st_mtime,
                })

            return {
                "path": str(path),
                "entries": entries,
                "count": len(entries),
                "success": True,
            }

        except Exception as e:
            return {
                "path": str(path),
                "error": str(e),
                "success": False,
            }

    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get file/directory metadata.

        Args:
            path: File or directory path.

        Returns:
            Dictionary with metadata or error.
        """
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return {
                    "path": str(path),
                    "error": f"Path not found: {path}",
                    "success": False,
                }

            stat = file_path.stat()

            return {
                "path": str(path),
                "type": "dir" if file_path.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "exists": True,
                "success": True,
            }

        except Exception as e:
            return {
                "path": str(path),
                "error": str(e),
                "success": False,
            }

    async def exists(self, path: str) -> bool:
        """Check if a path exists.

        Args:
            path: Path to check.

        Returns:
            True if exists, False otherwise.
        """
        return self._resolve_path(path).exists()

    async def create_directory(self, path: str) -> Dict[str, Any]:
        """Create a directory.

        Args:
            path: Directory path.

        Returns:
            Dictionary with result or error.
        """
        try:
            dir_path = self._resolve_path(path)
            dir_path.mkdir(parents=True, exist_ok=True)

            return {
                "path": str(path),
                "success": True,
            }

        except Exception as e:
            return {
                "path": str(path),
                "error": str(e),
                "success": False,
            }


# Convenience functions
async def read_file(path: str) -> Dict[str, Any]:
    """Read a file."""
    tool = FileOpsTool()
    return await tool.read_file(path)


async def write_file(path: str, content: str) -> Dict[str, Any]:
    """Write to a file."""
    tool = FileOpsTool()
    return await tool.write_file(path, content)


async def read_json(path: str) -> Dict[str, Any]:
    """Read a JSON file."""
    tool = FileOpsTool()
    return await tool.read_json(path)


async def write_json(path: str, data: Any) -> Dict[str, Any]:
    """Write a JSON file."""
    tool = FileOpsTool()
    return await tool.write_json(path, data)
