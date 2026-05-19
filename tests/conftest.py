"""Shared pytest fixtures for Excel ingestion tests."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest


class FakeUpload:
    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self._data

    def read(self) -> bytes:
        return self._data

    def seek(self, _pos: int) -> None:
        return None


@pytest.fixture
def sample_accounting_rows() -> list[dict]:
    return [
        {"交易日期": "2026-05-01", "帳號": "A001", "金額": 1000, "代號": "2330"},
        {"交易日期": "2026-05-02", "帳號": "A002", "金額": 2500, "代號": "2317"},
    ]


@pytest.fixture
def xlsx_bytes(sample_accounting_rows: list[dict]) -> bytes:
    buffer = BytesIO()
    pd.DataFrame(sample_accounting_rows).to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


@pytest.fixture
def xlsx_upload(xlsx_bytes: bytes) -> FakeUpload:
    return FakeUpload("ledger.xlsx", xlsx_bytes)


@pytest.fixture
def empty_xlsx_bytes() -> bytes:
    buffer = BytesIO()
    pd.DataFrame(columns=["交易日期", "帳號", "金額"]).to_excel(
        buffer, index=False, engine="openpyxl"
    )
    return buffer.getvalue()


@pytest.fixture
def invalid_date_xlsx_bytes() -> bytes:
    buffer = BytesIO()
    pd.DataFrame(
        [
            {"交易日期": "not-a-date", "帳號": "A001", "金額": 100},
            {"交易日期": "also-bad", "帳號": "A002", "金額": 200},
        ]
    ).to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()
