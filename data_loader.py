"""Backward-compatible shim — use reporting.ingestion.file_bundle instead."""

from reporting.ingestion.file_bundle import load_uploaded_files
from reporting.ingestion.excel_reader import read_excel_bytes, read_excel_path
from reporting.mapping.column_mapper import apply_auto_mapping as normalize_columns

__all__ = ["load_uploaded_files", "read_excel_bytes", "read_excel_path", "normalize_columns"]
