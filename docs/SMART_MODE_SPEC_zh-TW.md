# Smart Mode 規格與實作清單（桌面版）

> 適用範圍：`report_desktop_app`（PySide6）  
> 目標：讓工具可自動學習、降低人工重複操作、提高大型 Excel 處理流暢度與穩定性。  
> 規劃週期：2 個 Sprint（每個 Sprint 約 2 週）

---

## 1) 要解決的核心痛點

1. 每次都要手動做相同映射與範圍設定。  
2. 大檔案處理時等待久、重跑成本高。  
3. 產報前錯誤常在最後一步才爆出。  
4. 同仁交接時流程不一致，難以複製最佳作業方式。

---

## 2) Smart Mode 產品定義

Smart Mode = 在既有流程（匯入 → 映射 → 驗證 → 預覽 → 產報）上，新增 4 個「智慧層」：

- **智慧建議（Advisor）**：提供欄位映射 Top-N 建議與信心分數。
- **智慧記憶（Profile）**：記住使用者/來源檔案習慣並自動套用 preset。
- **智慧檢查（Health Check）**：在早期就提示缺欄、型別、期間與金額異常。
- **智慧執行（Smooth Pipeline）**：支援增量快取、背景可取消、失敗可續跑。

---

## 3) 非目標（避免 scope 失控）

- 不在此階段引入雲端服務或外部 LLM API。  
- 不重寫既有 `reporting/pipeline.py` 主邏輯，只在桌面端做包裝增強。  
- 不更動使用者既有操作路徑，Smart Mode 預設為「可關閉」。

---

## 4) 功能規格（MVP）

## 4.1 智慧欄位映射 Advisor

**使用時機**：檔案匯入完成、開啟欄位映射前。  
**輸出**：每個 canonical 欄位提供 1~3 個候選來源欄位，附信心分數與理由。

評分來源（加權）：
- 欄名相似度（normalize + token 比對）
- 值型態分數（日期、數值、字串模式）
- 值分布分數（空值率、唯一值比例、正負值分布）
- 歷史成功映射加成（同檔名模式/同欄名）

建議門檻：
- `score >= 0.85`：自動預選
- `0.60 <= score < 0.85`：列為建議但不自動套用
- `< 0.60`：不建議

---

## 4.2 智慧記憶 Profile

依下列 key 記錄最近成功設定：
- 檔名模式（例如 `brokerA_*`）
- 工作表名稱
- 欄位集合指紋（sorted column names hash）

記憶內容：
- mapping preset id
- range preset id
- report type（daily/weekly/monthly）
- 最近成功日期與次數

套用策略：
- 高信心（同指紋）直接建議「一鍵套用」
- 中信心（檔名模式符合）顯示「建議套用」
- 低信心只列歷史參考

---

## 4.3 前置健康檢查 Health Check

在「預覽轉換」前先跑，並可單獨執行。

檢查項：
- 必要欄位缺失
- 日期欄位不可解析比例
- 金額欄位非數值比例
- 重複交易鍵（可配置 key 欄位）
- 期間越界（超出報表日期區間）

結果分級：
- `ERROR`：禁止產報（需修正）
- `WARN`：可產報但顯示風險
- `INFO`：提醒訊息

---

## 4.4 Smooth Pipeline（流暢處理）

能力：
- **增量快取**：輸入檔 hash 與映射未變更時，跳過重複轉換步驟。
- **背景取消**：長任務可取消，UI 不凍結。
- **失敗續跑**：保留最後成功階段 checkpoint，允許重試從中段繼續。
- **監看去重**：資料夾監看匯入時，避免同檔反覆加入。

---

## 5) 資料與設定設計

## 5.1 新增設定檔

- `config/smart_mode.yaml`
  - `enabled: true`
  - `advisor.auto_apply_threshold: 0.85`
  - `advisor.suggest_threshold: 0.60`
  - `health.required_fields: [...]`
  - `pipeline_cache.enabled: true`
  - `watch_dedup.enabled: true`

## 5.2 本機資料儲存（JSON）

建議放在 `report_desktop_app/data/`：
- `smart_profiles.json`：歷史習慣與成功紀錄
- `pipeline_cache_index.json`：快取索引（input hash -> stage outputs）

---

## 6) 程式碼落點（建議）

### 新增檔案

- `report_desktop_app/app/services/smart_mapping_advisor.py`
- `report_desktop_app/app/services/smart_profile_service.py`
- `report_desktop_app/app/services/health_check_service.py`
- `report_desktop_app/app/services/pipeline_cache_service.py`

### 既有檔案調整

- `report_desktop_app/app/application/app_controller.py`
  - 串接 advisor / profile / health check / cache
- `report_desktop_app/app/ui/dialogs.py`
  - 在 MappingDialog 顯示建議映射與信心分數
- `report_desktop_app/app/ui/main_window.py`
  - 新增 Smart Mode 開關、健康檢查入口與狀態提示
- `report_desktop_app/app/core/schemas.py`
  - 新增 advisor/health 的 DTO
- `report_desktop_app/app/services/folder_import.py`
  - 匯入去重策略（hash + mtime + size）

---

## 7) Sprint 拆解（可直接排程）

## Sprint 1（MVP 智慧化）

1. 建立 `smart_mode.yaml` 與資料 schema。  
2. 完成 `smart_mapping_advisor.py`（規則式評分，不引入模型）。  
3. 完成 `smart_profile_service.py`（讀寫 JSON + 套用策略）。  
4. 在 MappingDialog 加入「建議映射」UI（可一鍵套用）。  
5. 新增測試：
   - `tests/test_smart_mapping_advisor.py`
   - `tests/test_smart_profile_service.py`

**Sprint 1 驗收**
- 匯入已知格式檔案，70% 以上欄位可被正確建議。  
- 第二次同類檔案匯入，可在 1 次點擊內完成映射。  
- 不影響既有映射 preset 流程。

## Sprint 2（流暢度與穩定）

1. 完成 `health_check_service.py` 與 UI 警示呈現。  
2. 完成 `pipeline_cache_service.py`（至少支援轉換前後中介快取）。  
3. AppController 任務取消 + checkpoint 續跑。  
4. folder watch 匯入去重與節流。  
5. 新增測試：
   - `tests/test_health_check_service.py`
   - `tests/test_pipeline_cache_service.py`

**Sprint 2 驗收**
- 同檔重跑時間降低 40% 以上（視資料量可調）。  
- 大檔處理可取消且 UI 不凍結。  
- 產報前錯誤可在健康檢查階段提早發現。

---

## 8) 品質與效能 KPI（建議）

- 映射自動建議採納率 >= 60%  
- 平均產報準備時間下降 >= 30%  
- 產報前阻斷型錯誤（ERROR）在早期發現比例 >= 80%  
- folder watch 重複匯入率 < 1%

---

## 9) 風險與對策

- **風險：錯誤自動映射造成錯帳**  
  - 對策：只自動套用高信心建議；低信心需人工確認。
- **風險：快取污染導致結果不一致**  
  - 對策：快取 key 納入 mapping hash、日期條件、版本號。
- **風險：UI 變複雜**  
  - 對策：Smart Mode 提示採漸進揭露，預設不干擾主流程。

---

## 10) 下一步（建議立即執行）

1. 先落地 Sprint 1（Advisor + Profile + Mapping UI）。  
2. 一週後收集 5~10 份真實檔案的建議命中率。  
3. 依命中率再調整評分權重，再進入 Sprint 2。

