"""
Qt model/view adapter for displaying pandas DataFrames in QTableView.

Use one model instance per preview source (e.g. raw import vs transformed).
Call set_dataframe() when the underlying data changes.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


def format_cell_value(value: Any) -> str:
    """
    Convert a single cell value to a display string.

    Kept module-level so unit tests can run without QWidget.
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return str(value)

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


class DataFrameTableModel(QAbstractTableModel):
    """
    Read-only QAbstractTableModel backed by a pandas DataFrame.

    - Column names are shown as horizontal headers.
    - Row labels use the DataFrame index when present; otherwise 1-based numbers.
    - Empty frames (0 rows) are safe; columns still produce headers when defined.
    - All cell values are returned as strings for DisplayRole and EditRole.
    """

    def __init__(self, dataframe: pd.DataFrame | None = None, parent=None) -> None:
        super().__init__(parent)
        self._dataframe = self._coerce(dataframe)

    @staticmethod
    def _coerce(dataframe: pd.DataFrame | None) -> pd.DataFrame:
        if dataframe is None:
            return pd.DataFrame()
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas.DataFrame or None")
        return dataframe.copy()

    def dataframe(self) -> pd.DataFrame:
        """Return a copy of the backing DataFrame."""
        return self._dataframe.copy()

    def set_dataframe(self, dataframe: pd.DataFrame | None) -> None:
        """Replace the backing data and notify views."""
        self.beginResetModel()
        self._dataframe = self._coerce(dataframe)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._dataframe.index)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._dataframe.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # noqa: N802
        if not index.isValid():
            return None
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None

        row, col = index.row(), index.column()
        if row < 0 or col < 0 or row >= self.rowCount() or col >= self.columnCount():
            return None

        return format_cell_value(self._dataframe.iat[row, col])

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._dataframe.columns):
                return str(self._dataframe.columns[section])
            return None

        if orientation == Qt.Orientation.Vertical:
            if 0 <= section < len(self._dataframe.index):
                label = self._dataframe.index[section]
                return "" if pd.isna(label) else str(label)
            return str(section + 1)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:  # noqa: N802
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
