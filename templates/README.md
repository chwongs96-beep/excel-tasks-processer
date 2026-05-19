# Excel 報表範本

此目錄存放日/週/月報表的 `.xlsx` 範本。首次執行 `report_builder` 時若檔案不存在會自動建立。

版面對應關係定義於 [`config/template_mapping.yaml`](../config/template_mapping.yaml)。

手動調整範本時請保留：

- 中繼資料儲存格（B2–B4）：報表標題、期間、產生時間
- 第 4 列：欄位標題樣式（資料從 A5 開始寫入）
