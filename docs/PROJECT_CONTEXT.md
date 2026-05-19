# 專案脈絡記憶（Session Context）

> **用途**：新對話請 `@docs/PROJECT_CONTEXT.md` 或依 `.cursor/rules` 自動載入。  
> **最後更新**：2026-05-19  
> **專案路徑**：`C:\Users\CheChe\.cursor\projects\empty-window`  
> **原始計畫**：`C:\Users\CheChe\.cursor\plans\會計報表自動化工具_14fd6da6.plan.md`（勿編輯）

---

## 1. 專案目標

**證券會計 Excel 報表工具**（內部使用，**僅桌面版**）：

- **UI**：PySide6 — [`report_desktop_app/`](report_desktop_app/)
- **核心**：`reporting/` + `transformer.py` + `report_builder.py`
- **流程**：匯入 Excel → 欄位映射（preset）→ 驗證 → 預覽 → 產生日/週/月報
- **Streamlit 網頁版已移除**（2026-05-19）

---

## 2. 架構與資料流

```
report_desktop_app/main.py
  → MainWindow / AppController
  → 產報：pipeline_runner → run_report(export=False) + ReportGeneratorService.export
  → 預覽：本機 TransformerService

reporting/pipeline.run_report()
  1. validate_date_selection / validate_mapping
  2. load_uploaded_files
  3. normalize_canonical_frame
  4. transform_for_report(skip_normalize=True)
  5. （桌面）export 由 report_desktop_app 寫入自訂範本路徑
```

### 關鍵路徑

| 路徑 | 職責 |
|------|------|
| `report_desktop_app/main.py` | **應用程式進入點** |
| `report_desktop_app/app/application/app_controller.py` | 用例編排 |
| `report_desktop_app/app/services/pipeline_runner.py` | 共用 `run_report` 轉換 |
| `reporting/pipeline.py` | 端到端管線 |
| `transformer.py` | 彙總主邏輯 |
| `report_builder.py` | 範本 Excel 匯出（Streamlit 時亦用；桌面 export 參考） |
| `app_config.py` | Python 設定（`config/` 為 YAML） |

---

## 3. 啟動與測試

```powershell
cd report_desktop_app
pip install -r requirements.txt
python main.py
```

```powershell
# repo 根目錄
python -m pytest -q
```

---

## 4. 桌面版功能狀態

| 項目 | 狀態 |
|------|------|
| PySide6 UI v0.2.0 | ✅ |
| 映射 preset | ✅ |
| `run_report` 整合 | ✅ `pipeline_runner` |
| PyInstaller | ✅ `report_desktop_app/pyinstaller.spec` |

---

## 5. 已完成重構（P1–P3）

見先前 Phase 記錄：`dates`、`safe_io`、`filenames`、`app_config`、測試合併、`pipeline_runner`。

---

## 6. 使用者偏好

- 回覆語言：**繁體中文**
- 不要主動 git commit / push
- 勿編輯 `會計報表自動化工具_14fd6da6.plan.md`
- **僅保留桌面版**，不要恢復 Streamlit

---

## 7. 變更紀錄

| 日期 | 內容 |
|------|------|
| 2026-05-19 | 移除 Streamlit（`app.py`、`app_ui/`）；README 改為桌面專用 |
| 2026-05-19 | 重構 Phase 1–3、桌面版上線收尾 |
