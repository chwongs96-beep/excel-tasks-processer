# 證券會計報表工具（桌面版）

內部使用的 PySide6 桌面應用：匯入 Excel、映射欄位、驗證資料、預覽轉換結果，並依範本產生日/週/月報表。

## 環境需求

- Python 3.11+
- Windows（建議；macOS / Linux 亦可）

## 安裝

```powershell
cd report_desktop_app
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

開發與測試可額外安裝：`pip install -r requirements-dev.txt`

## 啟動

```powershell
python main.py
```

## 專案結構

```text
report_desktop_app/
├── main.py                 # 程式進入點
├── app/
│   ├── ui/                 # PySide6 視窗、背景任務、對話框
│   ├── application/        # AppController、ImportSession
│   ├── services/           # Excel、驗證、轉換、產報
│   ├── core/               # 設定、DTO、路徑、日期、日誌
│   ├── templates/          # Excel 範本
│   └── assets/icons/
├── output/                 # 預設輸出目錄
├── docs/PACKAGING.md       # PyInstaller 打包說明
└── tests/
```

## 測試

```powershell
python -m pytest -q
```

## 與父 repo 的關係

父目錄提供共用 `reporting/`、`config/*.yaml`、`transformer.py`。本應用為**唯一 UI**（Streamlit 版已移除）。`app/core/reporting_bridge.py` 載入父套件；產報經 `pipeline_runner` 呼叫 `run_report()`。

## 工作流程

### 合併多檔為單一 Excel

1. **新增** 多個 `.xlsx` / `.xls`
2. （選用）選檔後按 **設定範圍…** — 工作表、標題列、列範圍或 `B2:H500`
3. **合併至單一 Excel…** — 三步精靈：確認檔案 → 各檔範圍 → 輸出  
   - **單一工作表** 或 **每檔一個工作表**  
   - 可勾選 **使用範本建立新檔案**
4. 合併檔可再匯入，接續欄位映射與產報

### 產生日／週／月報表

1. 匯入 → **欄位映射**（可載入 preset）→ **驗證** → **預覽轉換** → **產生報表**

## 目前版本（0.4.0）

- 匯入 Excel、**從資料夾匯入**、**資料夾監看**（每 60 秒自動匯入新檔）
- **調整分錄**：另選 Excel，產報時併入（`_entry_type=adjustment`）
- **批次產生日報**：日期區間一次產多份
- 多檔範圍／合併／對帳（差異顯示於「對帳差異」分頁）
- 操作紀錄：`logs/operations.jsonl`
