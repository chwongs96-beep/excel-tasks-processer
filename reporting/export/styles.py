"""openpyxl style definitions for report workbooks."""

from __future__ import annotations

from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.styles.numbers import FORMAT_NUMBER_COMMA_SEPARATED1

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")

DATE_FORMAT = "yyyy-mm-dd"
AMOUNT_FORMAT = FORMAT_NUMBER_COMMA_SEPARATED1

DATE_COLUMNS = frozenset({"trade_date"})
AMOUNT_COLUMNS = frozenset({"amount", "debit", "credit"})
