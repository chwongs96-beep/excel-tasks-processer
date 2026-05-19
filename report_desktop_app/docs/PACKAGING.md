# 桌面版打包說明

## 執行環境

- Python 3.11+
- 依賴：見 `report_desktop_app/requirements.txt`
- 開發模式：父專案 `config/*.yaml` 從 repo 根目錄載入
- 凍結後：`config/` 隨執行檔打包；範本可於首次產報時 bootstrap 至 `%APPDATA%/SecuritiesReporting/templates/`

## 開發執行

```powershell
cd report_desktop_app
pip install -r requirements.txt
python main.py
```

## PyInstaller（one-folder）

1. 安裝開發依賴（含 PyInstaller）：

```powershell
cd report_desktop_app
pip install -r requirements-dev.txt
```

2. 建置：

```powershell
.\scripts\build_desktop.ps1
```

或手動：

```powershell
cd report_desktop_app
pyinstaller --noconfirm --clean pyinstaller.spec
```

3. 輸出目錄：`report_desktop_app/dist/SecuritiesReportDesktop/`
4. 執行：`dist\SecuritiesReportDesktop\SecuritiesReportDesktop.exe`

`pyinstaller.spec` 會打包：

- `../config/*.yaml` 與 `mapping_presets/`
- `app/templates/*.xlsx`（若存在）
- 父 repo `reporting/` 套件（透過 `pathex` + `hiddenimports`）

路徑解析見 `app/core/paths.py`（`is_frozen()`、`user_data_dir()`）。

## 日誌與輸出

- 日誌：`LOGS_DIR/app.log`（開發：`report_desktop_app/logs/`；凍結：`%APPDATA%/SecuritiesReporting/logs/`）
- 報表輸出：預設 `output/`（可在 UI 變更）

## 測試

```powershell
cd report_desktop_app
python -m pytest -q
```
