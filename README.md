# Y3W7

三年七萬課程自動化報名（勞動部勞動力發展署 OJT）。

到指定時間前自動登入、辨識圖形驗證碼，並在開搶時間執行課程報名。

## 環境需求

- Python 3.10+（建議）
- Google Chrome（本機已安裝）
- Windows / macOS / Linux

## 安裝

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install selenium ddddocr
```

## 使用方式

```bash
python main.py ^
  --email 你的Email ^
  --password 你的密碼 ^
  --ocid 課程OCID ^
  --target_time 11:59:55 ^
  --ahead 300 ^
  --retry 5
```

macOS / Linux 把 `^` 改成 `\` 即可。

### 參數說明

| 參數 | 必填 | 預設值 | 說明 |
|------|------|--------|------|
| `--email` | 是 | — | 登入用 Email |
| `--password` | 是 | — | 登入用密碼 |
| `--ocid` | 是 | — | 課程 OCID（課程詳情網址中的 `OCID=`） |
| `--target_time` | 否 | `11:59:55` | 開搶時間，格式 `HH:mm:ss` |
| `--ahead` | 否 | `300` | 提前幾秒開始登入（預設目標時間前 5 分鐘） |
| `--retry` | 否 | `5` | 「我要報名」重試次數 |

### 執行流程

1. 等待至 `target_time` 前 `ahead` 秒
2. 開啟 Chrome → 登入（自動辨識驗證碼）
3. 進入課程頁
4. 精確等到 `target_time` 後執行報名

### 範例

```bash
python main.py --email demo@example.com --password "your-password" --ocid 171564 --target_time 12:00:00 --ahead 300
```

## 輸出成執行檔（Windows）

使用 [PyInstaller](https://pyinstaller.org/) 打包。  
**請一定要用「已安裝 `ddddocr` 的同一個虛擬環境」來打包**，否則執行檔會出現 `No module named 'ddddocr'`。

### 正確做法（建議）

```bash
# 1. 啟用虛擬環境
.venv\Scripts\activate

# 2. 確認套件都在這個環境裡
pip install selenium ddddocr pyinstaller
python -c "import ddddocr; print(ddddocr.__file__)"

# 3. 用「虛擬環境內」的 pyinstaller 打包（不要用系統全域的）
python -m PyInstaller --noconfirm --clean course_register.spec
```

或直接下指令（等同於使用專案內的 `.spec`）：

```bash
python -m PyInstaller --noconfirm --clean --onefile --console ^
  --name course_register ^
  --hidden-import=ddddocr ^
  --collect-all ddddocr ^
  --collect-all onnxruntime ^
  --collect-all cv2 ^
  --collect-submodules ddddocr ^
  main.py
```

完成後執行檔位於：

```text
dist\course_register.exe
```

執行方式：

```bash
dist\course_register.exe --email demo@example.com --password "your-password" --ocid 171564 --target_time 12:00:00
```

### 常見錯誤：找不到 ddddocr

| 原因 | 解法 |
|------|------|
| 用系統全域 `pyinstaller` 打包，但 `ddddocr` 只裝在 `.venv` | 先 `activate`，再用 `python -m PyInstaller ...` |
| 只下了 `pyinstaller ...`，實際呼叫到別套 Python | 改用 `python -m PyInstaller`（看得到哪個 Python） |
| 模型 / 子模組沒被打進去 | 使用專案內 `course_register.spec`，或加上 `--collect-all ddddocr --collect-submodules ddddocr` |
| 執行檔過小（約十幾 MB） | 幾乎代表沒包到 OCR 依賴；正常打包後通常會大很多（常 >50MB） |

打包前可自檢：

```bash
where python
where pyinstaller
python -c "import ddddocr, selenium, PyInstaller; print('ok')"
```

三者應都指向 `.venv\Scripts\`。

### 打包注意事項

- 本機仍需安裝 **Google Chrome**（Selenium 會啟動瀏覽器）
- `--onefile` 第一次啟動可能較慢（解壓暫存檔）
- 若 onefile 仍有模組問題，改用資料夾模式較穩：

```bash
python -m PyInstaller --noconfirm --clean --onedir --console ^
  --name course_register ^
  --hidden-import=ddddocr ^
  --collect-all ddddocr ^
  --collect-all onnxruntime ^
  --collect-all cv2 ^
  --collect-submodules ddddocr ^
  main.py
```

執行檔改為 `dist\course_register\course_register.exe`。

## 注意

- 請僅用於自己的帳號與合法用途
- 驗證碼辨識可能偶發失敗，程式會自動刷新重試
- 請勿把帳密寫進程式碼或提交到 Git
