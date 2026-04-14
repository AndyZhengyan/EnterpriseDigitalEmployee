# apps/ops/routers/oracle.py — Knowledge archive (read/write markdown documents)
import datetime
import os
import re
from pathlib import Path
from urllib.parse import unquote

import yaml
from fastapi import APIRouter, Depends, HTTPException

from apps.ops._auth import verify_api_key
from apps.ops.db import BASE_DIR

router = APIRouter(prefix="/api/oracle", tags=["oracle"])

ORACLE_DIR = Path(os.environ.get("ORACLE_DIR", str(BASE_DIR / "data" / "oracle")))


def _read_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown string. Returns (meta_dict, body_string)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content
    meta = yaml.safe_load(content[4:end]) or {}
    body = content[end + 5 :]
    return meta, body


def _scan_archives(source_filter: str | None = None) -> list[dict]:
    """Scan oracle directories for .md files and return their metadata."""
    archives = []
    dirs_to_scan = ["avatar", "import"] if not source_filter else [source_filter]
    for sd in dirs_to_scan:
        d = ORACLE_DIR / sd
        if not d.is_dir():
            continue
        for f in d.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            meta, body = _read_frontmatter(content)
            slug = f.stem
            # Extract summary: first non-empty line of body, stripped, max 100 chars
            summary = ""
            if body:
                first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
                summary = first_line[:100]
            archives.append(
                {
                    "id": slug,
                    "title": meta.get("title", slug),
                    "source": sd,
                    "contributor": meta.get("contributor", ""),
                    "createdAt": meta.get("created_at", ""),
                    "tags": meta.get("tags", []),
                    "summary": summary,
                    "path": f"{sd}/{f.name}",
                }
            )
    return sorted(archives, key=lambda a: a.get("createdAt", ""), reverse=True)


@router.get("/archives")
def list_archives(source: str | None = None, _: bool = Depends(verify_api_key)):
    """List all archives, optionally filtered by source (avatar | import)."""
    items = _scan_archives(source_filter=source)
    return {"total": len(items), "items": items}


@router.get("/archives/{archive_id}")
def get_archive(archive_id: str, _: bool = Depends(verify_api_key)):
    """Get a single archive by slug (filename without .md). archive_id is URL-decoded."""
    archive_id = unquote(archive_id)
    for sd in ["avatar", "import"]:
        fp = ORACLE_DIR / sd / f"{archive_id}.md"
        if fp.exists():
            content = fp.read_text(encoding="utf-8")
            meta, body = _read_frontmatter(content)
            return {
                "meta": {
                    "id": archive_id,
                    "title": meta.get("title", archive_id),
                    "source": sd,
                    "contributor": meta.get("contributor", ""),
                    "createdAt": meta.get("created_at", ""),
                    "tags": meta.get("tags", []),
                },
                "content": body.strip(),
            }
    raise HTTPException(status_code=404, detail="Archive not found")


@router.post("/archives/upload")
def upload_archive(req: dict, _: bool = Depends(verify_api_key)):
    """Upload a new archive. Creates a .md file under data/oracle/{source}/."""
    title = req.get("title", "").strip()
    source = req.get("source", "import")
    body_content = req.get("content", "")
    contributor = req.get("contributor", "管理员")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if source not in ("avatar", "import"):
        raise HTTPException(status_code=400, detail="source must be 'avatar' or 'import'")
    safe_slug = re.sub(r"[^\w\s-]", "", title).replace(" ", "-").replace("\n", "-")
    created_at = datetime.date.today().isoformat()
    fp = ORACLE_DIR / source / f"{safe_slug}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    if fp.exists():
        raise HTTPException(status_code=409, detail="Archive with this title already exists")
    fm_dict = {
        "title": title,
        "source": source,
        "contributor": contributor,
        "created_at": created_at,
        "tags": [],
    }
    fm = yaml.safe_dump(fm_dict, allow_unicode=True, default_flow_style=False)
    fp.write_text(f"---\n{fm}---\n\n" + "\n" + body_content, encoding="utf-8")
    return {"id": safe_slug, "path": str(fp.relative_to(ORACLE_DIR)), "message": "上传成功"}
