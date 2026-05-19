"""User-facing help copy (Traditional Chinese)."""

from __future__ import annotations

RECONCILE_HELP_HTML = """
<h3>資料對帳在做什麼？</h3>
<p>會計實務上常要把<strong>兩套來源</strong>逐筆核對，例如：</p>
<ul>
  <li>券商成交明細（左檔／基準） vs 內部系統匯出（右檔）</li>
  <li>銀行對帳單 vs 總帳明細</li>
</ul>

<h3>比對邏輯（專業說明）</h3>
<ol>
  <li><strong>對帳鍵</strong>：您勾選的欄位組合成一筆交易的「唯一識別」
    （建議：交易日期 + 帳號/券代號；必要時再加流水號或委託單號）。</li>
  <li><strong>僅左邊</strong>：鍵在左檔存在、右檔找不到 → 可能漏登、右檔範圍不足。</li>
  <li><strong>僅右邊</strong>：鍵在右檔存在、左檔找不到 → 可能重複登錄、左檔缺漏。</li>
  <li><strong>金額不符</strong>：兩邊鍵相同，但指定金額欄差異 &gt; 容差
    → 可能匯率、手續費分錄、四捨五入或映射錯欄。</li>
</ol>

<h3>操作建議</h3>
<ul>
  <li>兩檔請先各自<strong>設定範圍</strong>，確保標題列與欄位一致。</li>
  <li>欄位名稱不同時，請先<strong>合併</strong>或統一欄名再對帳，或只勾選兩邊都有的欄位。</li>
  <li>完成後到主畫面 <strong>「對帳差異」</strong> 分頁預覽，並可匯出三個工作表供覆核留底。</li>
</ul>
"""

WORKFLOW_INTRO = (
    "標準產報：① 匯入 → ② 映射 → ③ 驗證 → ④ 預覽 → ⑤ 產報。"
    " 多檔合併：先匯入多個 Excel → 左側「合併」精靈（見 說明 → 合併與工作表流程）。"
)

CONSOLIDATE_AND_SHEETS_HELP_HTML = """
<h2>多檔 Excel 合併與工作表搬移 — 操作指南</h2>
<p>以下說明<strong>先做什麼、後做什麼</strong>，避免順序錯亂。適用任意數量的來源檔（10、20 檔皆可）。</p>

<h3>一、先決定您的目標</h3>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%;">
<tr>
  <th>您的需求</th><th>建議做法</th><th>結果</th>
</tr>
<tr>
  <td>多份資料的<strong>列</strong>要接在同一張表（像總明細）</td>
  <td>本工具 → 合併 →「<strong>合併到單一工作表</strong>」</td>
  <td>1 個 .xlsx，1 個工作表，多一欄 <code>_source_file</code> 標記來源檔名</td>
</tr>
<tr>
  <td>多份資料要<strong>各自一個分頁</strong>留在同一活頁簿</td>
  <td>本工具 → 合併 →「<strong>每個來源一個工作表</strong>」</td>
  <td>1 個 .xlsx，工作表數量＝來源檔數（以檔名命名）</td>
</tr>
<tr>
  <td>只搬移 Excel 內建分頁，不改欄位結構</td>
  <td>使用 <strong>Excel 內建</strong>「移動或複製工作表」（見下方第三節）</td>
  <td>格式、公式、圖表原樣保留</td>
</tr>
</table>

<h3>二、本工具：多個 Excel → 1 個 Excel（建議順序）</h3>
<ol style="line-height:1.6;">
  <li><strong>步驟 1 — 匯入來源</strong><br/>
    左側「資料來源」→ <em>新增檔案</em>（可一次選多個）或 <em>資料夾</em>。<br/>
    確認清單中出現全部檔名；處理進度視窗會列出每一檔的讀取步驟。</li>
  <li><strong>步驟 2 — 設定每檔範圍（重要）</strong><br/>
    對<strong>每一個</strong>檔案：選取清單列 → <em>範圍</em>（或連按兩下）。<br/>
    指定：工作表名稱、標題列、資料起迄列／欄。各檔結構不同就各設各的。<br/>
    若格式相同，可先設好一檔，在合併精靈步驟 2 用「套用到全部」。</li>
  <li><strong>步驟 3 — 執行合併精靈</strong><br/>
    左側 <em>合併</em> → 依精靈三步完成：
    <ul>
      <li><strong>步驟 1</strong>：確認所有來源檔</li>
      <li><strong>步驟 2</strong>：逐檔確認／調整範圍</li>
      <li><strong>步驟 3</strong>：輸出檔名、資料夾、合併模式（單表／每檔一表）、可選範本</li>
    </ul>
  </li>
  <li><strong>步驟 4 — 合併後（可選）</strong><br/>
    勾選「合併完成後自動匯入」→ 合併檔會加入左側清單。<br/>
    若要接著產報：再勾「開啟欄位映射」→ 依序 <em>映射 → 驗證 → 預覽 → 產報</em>。</li>
</ol>

<p>
  <strong>流程圖（本工具合併路徑）</strong><br/>
  匯入多檔 → 每檔設範圍 → 合併精靈 → 輸出 1 個 xlsx（進度視窗逐步顯示）
  →（可選）匯入合併檔 → 映射 → 驗證 → 預覽 → 產報
</p>

<h3>三、Excel 內建：把工作表移到另一個活頁簿</h3>
<p>適用於：來源檔已有完整分頁（含公式、格式），只想<strong>搬分頁</strong>，不需重新指定資料範圍。</p>
<ol style="line-height:1.6;">
  <li>同時開啟「來源活頁簿」與「目標活頁簿」（或新建空白活頁簿）。</li>
  <li>在來源檔底部，對要搬移的<strong>工作表標籤</strong>按右鍵。</li>
  <li>選擇「<strong>移動或複製…</strong>」（Move or Copy）。</li>
  <li>「移至活頁簿」選擇目標檔案；「之前工作表」選插入位置。</li>
  <li>要保留來源分頁請勾選「<strong>建立副本</strong>」；不勾則為<strong>移動</strong>（來源會消失）。</li>
  <li>重複 2～5 直到所有分頁都在目標活頁簿。</li>
</ol>

<h3>四、常見問題</h3>
<ul>
  <li><strong>欄位名稱不一致</strong>：單表合併前請先統一標題列，或合併後用「映射」對齊標準欄位。</li>
  <li><strong>只要其中幾個分頁</strong>：在「範圍」對話框選對工作表；Excel 搬分頁則在步驟 3 只選需要的標籤。</li>
  <li><strong>合併後列數不對</strong>：回頭檢查每檔的標題列與結束列是否含空白列。</li>
</ul>
"""

BUTTON_TOOLTIPS: dict[str, str] = {
    "add": "選擇一個或多個 Excel（.xlsx / .xls）加入工作階段。",
    "folder": "依檔名關鍵字篩選資料夾內 Excel；可存 preset、套用範圍、啟用監看。",
    "adjustment": "載入調整分錄表；產報時與來源明細合併（標記為 adjustment）。",
    "range": "指定工作表、標題列與儲存格範圍；可預覽或清除選定區域內容。",
    "clear_range": "選取檔案後，指定範圍並清除該區儲存格的值（直接寫回檔案）。",
    "mapping": "將 Excel 欄位對應到標準會計欄位（可載入映射 preset）。",
    "merge": "多檔→1檔：先匯入並設範圍，再開合併精靈（單表或每檔一工作表）。詳見 說明→合併與工作表流程。",
    "reconcile": "比對兩檔的對帳鍵與金額，找出僅左、僅右與金額差異。",
    "validate": "檢查檔案、映射、日期與資料品質（含重複列警告）。",
    "preview": "依映射轉成標準格式並顯示於「轉換後」分頁。",
    "generate": "依範本產生日／週／月報表至輸出資料夾。",
    "batch": "依日期區間一次產生多份日報（預設僅工作日）。",
}
