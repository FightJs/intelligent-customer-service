"""交付包落盘：目录、文件拷贝、sha256、zip、设备 Excel。"""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from pipeline.models import ManifestFile, utc_now_iso


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ensure_clean_dir(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            return
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_into_package(
    src: Path,
    package_dir: Path,
    dest_rel: str,
) -> Path:
    dest = package_dir / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return path


def build_equipment_xlsx(
    package_dir: Path,
    equipment_list: list[dict[str, Any]],
    brand: str,
) -> Path:
    """从 plan.equipment_list 生成设备表（可选产物）。"""
    wb = Workbook()
    ws = wb.active
    ws.title = '设备清单'
    headers = ['类别', '名称', '型号', '品牌', '数量', '价格档', '理由', '定制', 'knowledge_id']
    ws.append(headers)
    for item in equipment_list:
        ws.append([
            item.get('category', ''),
            item.get('name', ''),
            item.get('model', ''),
            item.get('brand', ''),
            item.get('qty', 1),
            item.get('unit_price_band', ''),
            item.get('reason', ''),
            '是' if item.get('is_custom') else '否',
            item.get('knowledge_id') if item.get('knowledge_id') is not None else '',
        ])
    dest = package_dir / 'docs' / 'equipment.xlsx'
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb.save(dest)
    return dest


def make_zip(package_dir: Path, zip_path: Path | None = None) -> Path:
    """打包目录为 zip（默认与 package 同级）。"""
    if zip_path is None:
        zip_path = package_dir.parent / f'{package_dir.name}.zip'
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(package_dir.rglob('*')):
            if file.is_file():
                zf.write(file, arcname=str(file.relative_to(package_dir)))
    return zip_path


def collect_manifest_files(package_dir: Path, kind_by_suffix: dict[str, str] | None = None) -> list[ManifestFile]:
    """遍历 package 目录，对每个文件计算 sha256（R5）。"""
    kind_by_suffix = kind_by_suffix or {
        '.pdf': 'plan_pdf',
        '.json': 'json',
        '.png': 'image',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.mp4': 'video',
        '.xlsx': 'equipment_xlsx',
        '.md': 'readme',
    }
    files: list[ManifestFile] = []
    for file in sorted(package_dir.rglob('*')):
        if not file.is_file():
            continue
        rel = str(file.relative_to(package_dir))
        if rel == 'manifest.json':
            continue  # manifest 自身不纳入 files（避免自引用 hash）
        kind = kind_by_suffix.get(file.suffix.lower(), 'other')
        if rel == 'README.md':
            kind = 'readme'
        elif rel.endswith('plan.json'):
            kind = 'plan_json'
        elif rel.endswith('plan.pdf'):
            kind = 'plan_pdf'
        files.append(
            ManifestFile(
                path=rel,
                kind=kind,
                sha256=sha256_file(file),
                bytes=file.stat().st_size,
            )
        )
    return files
