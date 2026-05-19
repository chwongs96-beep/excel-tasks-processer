# 證券會計報表工具（桌面版）

內部使用的 **PySide6 桌面應用**：匯入 Excel、映射欄位、驗證與預覽，產生日報／週報／月報。

核心邏輯在 [`reporting/`](reporting/)（與 [`transformer.py`](transformer.py)、[`report_builder.py`](report_builder.py)）；UI 在 [`report_desktop_app/`](report_desktop_app/)。

## 介面預覽

桌面版主畫面（PySide6，明亮配色）：

<img src="docs/assets/desktop-ui-main.png" width="920" alt="證券會計報表工具 — 桌面版主畫面">

| 區域 | 說明 |
|------|------|
| **左側欄** | ① 資料來源（匯入、映射、合併、對帳等）；② 報表設定；底部固定 **驗證／預覽／產生報表** |
| **工作流程列** | 匯入 → 映射 → 驗證 → 預覽 → 產報，完成步驟會標示進度 |
| **資料預覽** | 分頁：**原始**、**轉換後**、**對帳差異** |
| **操作日誌** | 匯入、驗證、產報等訊息與錯誤 |
| **狀態列** | 就緒訊息；**介面大小**（Ctrl + 滾輪亦可縮放） |

選單 **檢視 → 配色方案** 可切換明亮日光／天藍／珍珠白；**說明** 內含完整操作手冊。  
更細的欄位說明見 [使用者手冊 §3](docs/USER_GUIDE_zh-TW.md#3-介面總覽)。

> 開發者若要更新截圖：`cd report_desktop_app` 後執行 `python scripts/capture_ui_screenshot.py`，輸出至 `docs/assets/desktop-ui-main.png`。

## 環境需求

- Python 3.11+
- Windows（建議）

## 需要安裝的 Library（GitHub 可見）

安裝指令（桌面版）：

```powershell
cd report_desktop_app
pip install -r requirements.txt
```

主要套件（`report_desktop_app/requirements.txt`）：

- `PySide6`（桌面 UI）
- `pandas`（資料處理）
- `openpyxl`（讀寫 `.xlsx`）
- `xlrd`（讀取舊版 `.xls`）
- `pyyaml`（讀取 YAML 設定）
- `pytest`（測試）

開發/打包額外套件（`report_desktop_app/requirements-dev.txt`）：

- `pytest-qt`（Qt UI 測試）
- `pyinstaller`（桌面版打包）

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

## 使用者手冊（繁體中文）

詳細操作說明請見 **[docs/USER_GUIDE_zh-TW.md](docs/USER_GUIDE_zh-TW.md)**。  
程式內亦可從 **說明 → 完整使用手冊（繁體中文）** 開啟。

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

Smart Mode 智慧化規劃可參考 [`docs/SMART_MODE_SPEC_zh-TW.md`](docs/SMART_MODE_SPEC_zh-TW.md)。
