# 證券會計報表工具（桌面版）

內部使用的 **PySide6 桌面應用**：匯入 Excel、映射欄位、驗證與預覽，產生日報／週報／月報。

核心邏輯在 [`reporting/`](reporting/)（與 [`transformer.py`](transformer.py)、[`report_builder.py`](report_builder.py)）；UI 在 [`report_desktop_app/`](report_desktop_app/)。

## 環境需求

- Python 3.11+
- Windows（建議）

## 安裝與啟動

```powershell
cd report_desktop_app
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

若尚未安裝父目錄共用套件，可先：

```powershell
cd ..
pip install -r requirements.txt
```

或從 repo 根目錄：

```powershell
.\scripts\run_desktop.ps1
```

## 工作流程

1. **新增** Excel（`.xlsx` / `.xls`）
2. **欄位映射**（可載入 `config/mapping_presets/` 的 preset）
3. **驗證** → **預覽轉換** → **產生報表**
4. 輸出預設在 `report_desktop_app/output/`（可在 UI 變更）

測試用範例：`report_desktop_app/tests/fixtures/sample_ledger.xlsx`

## 設定

| 路徑 | 說明 |
|------|------|
| `config/*.yaml` | canonical 欄位、報表定義、範本映射 |
| `app_config.py` | Python 設定（`config.py` 為相容 shim） |
| `report_desktop_app/app/templates/` | Excel 範本（可自動 bootstrap） |

## 測試

```powershell
# 核心套件（repo 根目錄）
python -m pytest -q

# 桌面 UI（子目錄）
cd report_desktop_app
python -m pytest -q
```

## 打包

見 [`report_desktop_app/docs/PACKAGING.md`](report_desktop_app/docs/PACKAGING.md)。

## 接續開發

請先閱讀 [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md)。
