"""Tests for DataFrameTableModel (format_cell_value needs no Qt)."""

from __future__ import annotations

import pandas as pd
import pytest
from PySide6.QtCore import Qt

from app.ui.table_model import DataFrameTableModel, format_cell_value

pytest.importorskip("PySide6.QtCore")


def test_format_cell_value_handles_none_and_nan() -> None:
    assert format_cell_value(None) == ""
    assert format_cell_value(float("nan")) == ""
    assert format_cell_value(pd.NA) == ""


def test_format_cell_value_numbers_and_timestamps() -> None:
    assert format_cell_value(42) == "42"
    assert format_cell_value(3.0) == "3"
    assert format_cell_value(3.14) == "3.14"
    assert format_cell_value(pd.Timestamp("2024-06-01")) == "2024-06-01T00:00:00"


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def test_empty_dataframe_zero_rows_and_columns(qapp) -> None:
    model = DataFrameTableModel(pd.DataFrame())
    assert model.rowCount() == 0
    assert model.columnCount() == 0
    assert model.data(model.index(0, 0)) is None
    assert model.headerData(0, Qt.Orientation.Horizontal) is None


def test_empty_rows_but_column_headers(qapp) -> None:
    model = DataFrameTableModel(pd.DataFrame(columns=["trade_date", "amount"]))
    assert model.rowCount() == 0
    assert model.columnCount() == 2
    assert model.headerData(0, Qt.Orientation.Horizontal) == "trade_date"
    assert model.headerData(1, Qt.Orientation.Horizontal) == "amount"


def test_cells_display_as_strings(qapp) -> None:
    model = DataFrameTableModel(pd.DataFrame({"x": [1, 2.5], "y": [None, "ok"]}))
    assert model.data(model.index(0, 0)) == "1"
    assert model.data(model.index(1, 0)) == "2.5"
    assert model.data(model.index(0, 1)) == ""
    assert model.data(model.index(1, 1)) == "ok"


def test_set_dataframe_resets_model(qapp) -> None:
    model = DataFrameTableModel(pd.DataFrame({"a": [1]}))
    assert model.rowCount() == 1
    model.set_dataframe(pd.DataFrame(columns=["b"]))
    assert model.rowCount() == 0
    assert model.columnCount() == 1
    assert model.headerData(0, Qt.Orientation.Horizontal) == "b"
