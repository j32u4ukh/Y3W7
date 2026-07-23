import argparse
import datetime
import logging
import os
import sys
import time

import ddddocr
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

TIMEOUT = 20  # 等待元素最大秒數
CAPTCHA_IFRAME = "imgCapt1"
CAPTCHA_REFRESH_SELECTOR = "a[target='imgCapt1']"
_ocr = ddddocr.DdddOcr(show_ad=False)
logger = logging.getLogger("course_register")


def _resolve_log_dir() -> str:
    """日誌目錄固定為 dist/logs（腳本從專案根目錄；exe 則在 exe 旁的 logs）。"""
    if getattr(sys, "frozen", False):
        # course_register.exe 位於 dist/ → dist/logs
        return os.path.join(os.path.dirname(sys.executable), "logs")
    return os.path.join("dist", "logs")


def setup_logging(ocid: str) -> str:
    """同時輸出到終端機與檔案，檔名為 dist/logs/{日期}-{時間}-{ocid}.log。"""
    log_dir = _resolve_log_dir()
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.datetime.now()
    log_name = f"{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{ocid}.log"
    log_path = os.path.join(log_dir, log_name)

    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("日誌檔案: %s", log_path)
    return log_path


def login(driver: WebDriver, email: str, password: str):
    wait = WebDriverWait(driver, TIMEOUT)

    # 點擊會員登入（會導向 SSO 登入頁）
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[@href='/Member/Login']"))).click()
    logger.info("Click login button")

    # 輸入帳號密碼
    wait.until(EC.presence_of_element_located(
        (By.ID, "CPH1_txt_EmailId"))).send_keys(email)
    wait.until(EC.presence_of_element_located(
        (By.ID, "CPH1_txt_dwsp"))).send_keys(password)

    # 自動辨識驗證碼並填入（驗證碼圖在 iframe 內）
    captcha_code = solve_captcha(driver)
    logger.info(f"captcha_code: {captcha_code}")
    driver.switch_to.default_content()
    verify_input = wait.until(
        EC.presence_of_element_located((By.ID, "CPH1_txt_VerifyCode"))
    )
    verify_input.clear()
    verify_input.send_keys(captcha_code)

    # 點擊登入
    wait.until(EC.element_to_be_clickable((By.ID, "CPH1_btnLogin"))).click()
    logger.info("完成登入!!")


def solve_captcha(driver: WebDriver, retry: int = 10) -> str:
    """切換至驗證碼 iframe，以 ddddocr 辨識；失敗則刷新後重試。"""
    wait = WebDriverWait(driver, TIMEOUT)
    last_code = ""

    for attempt in range(1, retry + 1):
        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, CAPTCHA_IFRAME)))
        captcha_img = wait.until(
            EC.presence_of_element_located((By.ID, "imgCaptcha1"))
        )
        wait.until(lambda d: bool(
            d.find_element(By.ID, "imgCaptcha1").get_attribute("src")
        ))
        old_src = captcha_img.get_attribute("src") or ""

        img_bytes = captcha_img.screenshot_as_png
        raw = _ocr.classification(img_bytes)
        captcha_code = "".join(c for c in raw if c.isdigit())
        logger.info(f"[captcha {attempt}/{retry}] code={captcha_code!r} (raw={raw!r})")

        if _is_valid_captcha_code(captcha_code):
            driver.switch_to.default_content()
            return captcha_code

        last_code = captcha_code
        if attempt >= retry:
            break

        logger.info("辨識失敗，刷新驗證碼後重試...")
        _refresh_captcha(driver, old_src)

    driver.switch_to.default_content()
    raise TimeoutException(
        f"驗證碼辨識失敗，已重試 {retry} 次，最後結果: {last_code!r}"
    )


def _is_valid_captcha_code(code: str) -> bool:
    """此站驗證碼為純數字，常見 4～6 碼。"""
    return code.isdigit() and 4 <= len(code) <= 6


def _refresh_captcha(driver: WebDriver, old_src: str) -> str:
    """在主頁點擊刷新，並等待 iframe 內 #imgCaptcha1 的 src 變更。"""
    wait = WebDriverWait(driver, TIMEOUT)
    driver.switch_to.default_content()
    wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, CAPTCHA_REFRESH_SELECTOR)
    )).click()

    def src_changed(d: WebDriver) -> bool:
        try:
            d.switch_to.default_content()
            d.switch_to.frame(CAPTCHA_IFRAME)
            src = d.find_element(By.ID, "imgCaptcha1").get_attribute("src") or ""
            return bool(src) and src != old_src
        except Exception:
            return False

    wait.until(src_changed)
    new_src = driver.find_element(By.ID, "imgCaptcha1").get_attribute("src") or ""
    # 稍等圖片載入完成再截圖
    time.sleep(0.3)
    logger.info(f"Captcha refreshed → src={new_src}")
    driver.switch_to.default_content()
    return new_src


def check_information(driver: WebDriver):
    # 短時間等待即可
    wait = WebDriverWait(driver, 3)
    try:
        # 等待按鈕可點擊，如果 3 秒內沒出現就跳過
        confirm_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.btn.btn-info.btn-info-Confirm"))
        )
        confirm_btn.click()
        logger.info("Confirm button clicked")
    except TimeoutException:
        # 按鈕不存在，直接略過
        logger.info("Confirm button not found, skipping")


def register_course(target_time: str, driver: WebDriver, ocid: str):

    # 給定指定時間 HH:mm:ss，這個時間前，間隔 10 毫秒或 100 毫秒檢查一次，時間到了再繼續執行
    wait_until(target_time=target_time,
               threshold1=10, interval1=5,
               threshold2=1.5, interval2=1,
               threshold3=0, interval3=0.1)

    URL = f"https://ojt.wda.gov.tw/ClassSearch/Detail?PlanType=1&OCID={ocid}"
    logger.info(f"URL: {URL}")

    driver.get(URL)
    wait = WebDriverWait(driver, TIMEOUT)

    # 嘗試進行報名頁面
    if not signup_course(driver=driver, url=URL, retry=int(args.retry)):
        logger.info("報名流程失敗，結束程式 ❌")
        return

    # 等待「報名」按鈕出現並點擊
    # <button type="button" data-role="GoSignUp" class="btn-orange" title="報名">報名</button>
    go_sign_up_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@data-role='GoSignUp' and normalize-space(text())='報名']"))
    )
    driver.execute_script("arguments[0].click();", go_sign_up_btn)
    logger.info("Click GoSignUp button")

    """ 等待第一個確認 radio 並點選
    <input class="form-inline radioset" id="rdo_INSURED_Y" name="Detail.ISCHECK" title="請選擇是否確認(每次重新點選)" type="radio" value="Y">
    """
    radio1 = wait.until(
        EC.element_to_be_clickable((By.ID, "rdo_INSURED_Y"))
    )
    radio1.click()
    logger.info("選擇第一個確認")

    """ 等待第二個確認 radio 並點選  
    <input class="form-inline radioset" id="rdo_ISCHECK2_Y" name="Detail.ISCHECK2" title="請選擇是否確認上述為個人最新及正確資料(每次重新點選)" type="radio" value="Y">
    """
    radio2 = wait.until(
        EC.element_to_be_clickable((By.ID, "rdo_ISCHECK2_Y"))
    )
    radio2.click()
    logger.info("選擇第二個確認")

    """ 等待送出按鈕並點擊
    <button type="button" data-role="SaveData" class="btn-orange" title="送出報名資料">送出報名資料</button>
    """
    submit_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@data-role='SaveData' and @title='送出報名資料']"))
    )
    submit_button.click()

    # <button class="btn btn-info btn-info-Confirm">確定</button>
    # 等待彈出視窗，點擊「確定」
    confirm_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@class,'btn-info-Confirm') and normalize-space(text())='確定']"))
    )
    driver.execute_script("arguments[0].click();", confirm_btn)
    logger.info("Click confirm button on popup")

    """
    <h3 class="main-title main-title-blue"><i class="fas fa-edit space-right"></i>課程報名結果</h3>
    """
    # 等待課程報名結果頁面元素出現，確保報名成功
    try:
        result_title = WebDriverWait(driver, TIMEOUT * 3).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//h3[contains(@class,'main-title') and contains(text(),'課程報名結果')]")
            )
        )
        logger.info("課程報名完成，已出現報名結果頁面")
    except TimeoutException:
        logger.info("報名結果未出現，可能需人工確認")


def wait_until(target_time: str,
               threshold1: float, interval1: float,
               threshold2: float, interval2: float,
               threshold3: float, interval3: float):
    """
    固定三組混合等待直到指定時間 (HH:mm:ss)

    :param target_time: 目標時間 (格式 HH:mm:ss)
    :param threshold1: 第一組門檻 (秒)，delta > threshold1 時用 interval1
    :param interval1:  第一組 sleep 秒數
    :param threshold2: 第二組門檻 (秒)，delta > threshold2 時用 interval2
    :param interval2:  第二組 sleep 秒數
    :param threshold3: 第三組門檻 (秒)，delta > threshold3 時用 interval3
    :param interval3:  第三組 sleep 秒數
    """

    today_target = datetime.datetime.strptime(
        datetime.datetime.now().strftime("%Y-%m-%d") + " " + target_time,
        "%Y-%m-%d %H:%M:%S"
    )

    while True:
        now = datetime.datetime.now()
        delta = (today_target - now).total_seconds()
        # logger.info(f"Now: {now}, delta: {delta}")
        logger.info(f"⏱ {now.strftime('%H:%M:%S.%f')[:-3]} → delta={delta:.3f}s")

        if delta <= 0:
            break

        if delta > threshold1:
            time.sleep(interval1)
        elif delta > threshold2:
            time.sleep(interval2)
        elif delta > threshold3:
            time.sleep(interval3)
        else:
            break  # 小於等於最後門檻，直接結束迴圈


def signup_course(driver: WebDriver, url: str, retry: int = 5) -> bool:
    """
    嘗試報名課程。若成功進入下一步，返回 True。
    若多次嘗試仍未成功，返回 False。
    """
    wait = WebDriverWait(driver, 10)

    # 🔹 等待倒數計時消失或變成僅顯示時間的狀態
    try:
        wait.until(
            EC.text_to_be_present_in_element(
                (By.ID, "time"),
                "現在時間為"  # 只要元素內文字不再有「距離開始報名時間剩餘」
            )
        )
        # 確保「距離開始報名時間剩餘」文字不在元素裡
        wait.until_not(
            EC.text_to_be_present_in_element(
                (By.ID, "time"),
                "距離開始報名時間剩餘"
            )
        )
        logger.info("倒數計時結束 → 可以報名")
    except TimeoutException:
        logger.info("尚無法報名...")
        return False

    for attempt in range(retry):
        try:
            # 確保每次重試都從課程頁面開始
            driver.get(url)

            enroll_button = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[@data-role='EnterClass' and normalize-space(text())='我要報名']"
                ))
            )
            enroll_button.click()
            logger.info(f"Clicked '我要報名' (attempt {attempt+1})")

            # 檢查是否出現提示（尚未開放報名）
            if handle_alert_if_present(driver):
                continue  # 有提示 → 再重試
            else:
                logger.info("Signup successful or in progress ✅")
                return True  # 成功 → 結束

        except TimeoutException:
            logger.info(f"Attempt {attempt+1}: '我要報名' 按鈕未出現，重試中...")

    logger.info("All retry attempts failed ❌")
    return False  # 全部失敗


def handle_alert_if_present(driver, timeout=3) -> bool:
    """
    使用顯性等待檢查「尚未開放報名」提示是否存在。
    若存在 → 點擊確定，返回 True。
    若不存在或逾時 → 返回 False。
    """
    wait = WebDriverWait(driver, timeout)
    try:
        # 等待提示框出現（可見即可）
        alert_box = wait.until(
            EC.visibility_of_element_located((
                By.XPATH,
                "//div[contains(@class,'jconfirm-box')]"
                "//div[contains(@class,'blockAlertMessage') and contains(text(),'尚未開放報名')]"
            ))
        )

        # 等待「確定」按鈕可點擊
        confirm_button = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class,'jconfirm-box')]//button[contains(@class,'btn-info-Confirm')]"
            ))
        )
        confirm_button.click()
        logger.info("Alert detected → clicked '確定'")

        # 等待彈窗關閉
        wait.until_not(
            EC.presence_of_element_located((
                By.XPATH,
                "//div[contains(@class,'jconfirm-box')]"
            ))
        )
        logger.info("Alert closed → ready to retry")
        return True

    except TimeoutException:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Course Auto Register Script")
    parser.add_argument("--email", required=True, help="登入用 Email")
    parser.add_argument("--password", required=True, help="登入用密碼")
    parser.add_argument("--ocid", required=True, help="課程 OCID")
    parser.add_argument("--target_time", required=False,
                        default="00:00:00", help="目標時間 (格式 HH:mm:ss)")
    parser.add_argument("--ahead", type=int, required=False, default=300,
                        help="提前幾秒開始登入（預設 300，即目標時間前 5 分鐘）")
    parser.add_argument("--retry", type=int, required=False,
                        default=5, help="重試次數")
    args = parser.parse_args()
    setup_logging(args.ocid)

    # 1. 先等到目標時間前 N 秒，再啟動瀏覽器與登入
    logger.info(f"等待至目標時間 {args.target_time} 前 {args.ahead} 秒...")
    wait_until(target_time=args.target_time,
               threshold1=3600, interval1=60,
               threshold2=600, interval2=10,
               threshold3=args.ahead, interval3=5)

    driver = webdriver.Chrome()

    try:
        driver.get("https://ojt.wda.gov.tw/")

        # TODO: 點擊 <button class="btn btn-info btn-info-Confirm">確定</button>
        check_information(driver=driver)

        # 2. 登入（帳號、密碼、驗證碼）
        login(driver, email=args.email, password=args.password)

        # TODO: 點擊 <button class="btn btn-info btn-info-Confirm">確定</button>
        check_information(driver=driver)

        # 3. 切換到課程頁面，再執行報名流程（內含精確等到 target_time）
        register_course(target_time=args.target_time,
                        driver=driver, ocid=args.ocid)

    except Exception:
        logger.exception("程式執行發生例外")

    finally:
        # 結束瀏覽器
        driver.quit()
