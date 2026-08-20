from __future__ import annotations

from src.models.schema import FileFormat

_SYNONYMS: dict[FileFormat, list[str]] = {
    FileFormat.CSV: ["csv", "comma separated values", "comma-separated values", ".csv"],
    FileFormat.JSON: ["json", ".json"],
    FileFormat.GEOJSON: ["geojson", "geo-json", ".geojson"],
    FileFormat.SHAPEFILE: ["shapefile", "shp", ".shp"],
    FileFormat.XLSX: ["xlsx", "excel", "microsoft excel", ".xlsx", ".xls"],
    FileFormat.XML: ["xml", ".xml"],
    FileFormat.API: ["api", "rest api", "web service"],
}
_LOOKUP: dict[str, FileFormat] = {
    synonym: fmt for fmt, synonyms in _SYNONYMS.items() for synonym in synonyms
}


def normalize_file_format(raw_text: str | None) -> FileFormat:
    if not raw_text:
        return FileFormat.UNKNOWN
    key = raw_text.strip().lower()
    return _LOOKUP.get(key, FileFormat.OTHER if key else FileFormat.UNKNOWN)
