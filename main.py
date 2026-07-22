import argparse
import datetime
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

TIMEOUT = 20  # 等待元素最大秒數


def login(driver: WebDriver, email: str, password: str):
    wait = WebDriverWait(driver, TIMEOUT)

    # 點擊會員登入
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[@href='/Member/Login']"))).click()
    print("Click login button")

    # 輸入帳號密碼
    wait.until(EC.presence_of_element_located(
        (By.ID, "CPH1_txt_EmailId"))).send_keys(email)
    wait.until(EC.presence_of_element_located(
        (By.ID, "CPH1_txt_dwsp"))).send_keys(password)

    # 處理驗證碼 (iframe)
    captcha_code = input("captcha_code: ")
    print(f"captcha_code: {captcha_code}")

    # 切回主頁填寫驗證碼
    driver.switch_to.default_content()
    wait.until(EC.presence_of_element_located(
        (By.ID, "CPH1_txt_VerifyCode"))).send_keys(captcha_code)

    # 點擊登入
    wait.until(EC.element_to_be_clickable((By.ID, "CPH1_btnLogin"))).click()
    print("完成登入!!")


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
        print("Confirm button clicked")
    except TimeoutException:
        # 按鈕不存在，直接略過
        print("Confirm button not found, skipping")


def register_course(target_time: str, driver: WebDriver, ocid: str):
    URL = f"https://ojt.wda.gov.tw/ClassSearch/Detail?PlanType=1&OCID={ocid}"
    print(f"URL: {URL}")

    driver.get(URL)
    wait = WebDriverWait(driver, TIMEOUT)

    # 距離目標尚遠時，輪流點選選單假裝有在操作（約 20 分鐘間隔，越近越短）
    click_look_more(driver=driver, target_time=target_time)

    # 給定指定時間 HH:mm:ss，這個時間前，間隔 10 毫秒或 100 毫秒檢查一次，時間到了再繼續執行
    wait_until(target_time=target_time,
               threshold1=10, interval1=5,
               threshold2=1.5, interval2=1,
               threshold3=0, interval3=0.1)

    # 嘗試進行報名頁面
    if not signup_course(driver=driver, retry=int(args.retry)):
        print("報名流程失敗，結束程式 ❌")
        return

    # 等待「報名」按鈕出現並點擊
    # <button type="button" data-role="GoSignUp" class="btn-orange" title="報名">報名</button>
    go_sign_up_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@data-role='GoSignUp' and normalize-space(text())='報名']"))
    )
    driver.execute_script("arguments[0].click();", go_sign_up_btn)
    print("Click GoSignUp button")

    """ 等待第一個確認 radio 並點選
    <input class="form-inline radioset" id="rdo_INSURED_Y" name="Detail.ISCHECK" title="請選擇是否確認(每次重新點選)" type="radio" value="Y">
    """
    radio1 = wait.until(
        EC.element_to_be_clickable((By.ID, "rdo_INSURED_Y"))
    )
    radio1.click()
    print("選擇第一個確認")

    """ 等待第二個確認 radio 並點選  
    <input class="form-inline radioset" id="rdo_ISCHECK2_Y" name="Detail.ISCHECK2" title="請選擇是否確認上述為個人最新及正確資料(每次重新點選)" type="radio" value="Y">
    """
    radio2 = wait.until(
        EC.element_to_be_clickable((By.ID, "rdo_ISCHECK2_Y"))
    )
    radio2.click()
    print("選擇第二個確認")

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
    print("Click confirm button on popup")

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
        print("課程報名完成，已出現報名結果頁面")
    except TimeoutException:
        print("報名結果未出現，可能需人工確認")


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
        # print(f"Now: {now}, delta: {delta}")
        print(f"⏱ {now.strftime('%H:%M:%S.%f')[:-3]} → delta={delta:.3f}s")

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


def click_look_more(driver: WebDriver, target_time: str,
                    threshold1: float = 40 * 60, interval1: float = 20 * 60,
                    threshold2: float = 20 * 60, interval2: float = 10 * 60,
                    threshold3: float = 5 * 60, interval3: float = 2 * 60):
    """
    交替點擊「最新消息」與「常見問題」，模擬有在瀏覽，直到接近 target_time。
    距離目標越遠間隔越長（約 20 分鐘），越近間隔越短。

    :param target_time: 目標時間 (格式 HH:mm:ss)
    :param threshold1: 第一組門檻 (秒)，delta > threshold1 時用 interval1
    :param interval1:  第一組 sleep 秒數（預設 20 分鐘）
    :param threshold2: 第二組門檻 (秒)
    :param interval2:  第二組 sleep 秒數（預設 10 分鐘）
    :param threshold3: 第三組門檻 (秒)，小於等於此值就結束，交給精確 wait
    :param interval3:  第三組 sleep 秒數（預設 2 分鐘）
    """
    today_target = datetime.datetime.strptime(
        datetime.datetime.now().strftime("%Y-%m-%d") + " " + target_time,
        "%Y-%m-%d %H:%M:%S"
    )
    actions = [click_newest_information, click_ussual_information]
    idx = 0

    while True:
        now = datetime.datetime.now()
        delta = (today_target - now).total_seconds()
        print(f"👀 look_more {now.strftime('%H:%M:%S')} → delta={delta:.1f}s")

        if delta <= threshold3:
            print("接近目標時間，結束模擬操作")
            break

        try:
            actions[idx % 2](driver)
        except Exception as e:
            print(f"look_more click failed: {e}")
        idx += 1

        now = datetime.datetime.now()
        delta = (today_target - now).total_seconds()
        if delta <= threshold3:
            print("接近目標時間，結束模擬操作")
            break

        if delta > threshold1:
            sleep_sec = interval1
        elif delta > threshold2:
            sleep_sec = interval2
        else:
            sleep_sec = interval3

        # 不要睡過頭，預留 threshold3 給後續精確等待
        sleep_sec = min(sleep_sec, max(0.0, delta - threshold3))
        print(f"💤 sleep {sleep_sec:.0f}s before next click")
        time.sleep(sleep_sec)


def click_newest_information(driver: WebDriver):
    """
    1. /html/body/div[3]/div/div/ul/li[1] (最新消息)
    2. /html/body/div[3]/div/div/ul/li[1]/ul/li[1]/a (焦點消息)
    """
    wait = WebDriverWait(driver, TIMEOUT)
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "/html/body/div[3]/div/div/ul/li[1]"))).click()
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "/html/body/div[3]/div/div/ul/li[1]/ul/li[1]/a"))).click()
    print("Click newest information (焦點消息)")


def click_ussual_information(driver: WebDriver):
    """
    1. /html/body/div[3]/div/div/ul/li[9]/a (Q&A)
    2. /html/body/div[3]/div/div/ul/li[9]/ul/li/a (常見問題)
    """
    wait = WebDriverWait(driver, TIMEOUT)
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "/html/body/div[3]/div/div/ul/li[9]/a"))).click()
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "/html/body/div[3]/div/div/ul/li[9]/ul/li/a"))).click()
    print("Click usual information (常見問題)")


def signup_course(driver: WebDriver, retry: int = 5) -> bool:
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
        print("倒數計時結束 → 可以報名")
    except TimeoutException:
        print("尚無法報名...")
        return False

    for attempt in range(retry):
        try:
            enroll_button = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//a[@data-role='EnterClass' and normalize-space(text())='我要報名']"
                ))
            )
            enroll_button.click()
            print(f"Clicked '我要報名' (attempt {attempt+1})")

            # 檢查是否出現提示（尚未開放報名）
            if handle_alert_if_present(driver):
                continue  # 有提示 → 再重試
            else:
                print("Signup successful or in progress ✅")
                return True  # 成功 → 結束

        except TimeoutException:
            print(f"Attempt {attempt+1}: '我要報名' 按鈕未出現，重試中...")

    print("All retry attempts failed ❌")
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
        print("Alert detected → clicked '確定'")

        # 等待彈窗關閉
        wait.until_not(
            EC.presence_of_element_located((
                By.XPATH,
                "//div[contains(@class,'jconfirm-box')]"
            ))
        )
        print("Alert closed → ready to retry")
        return True

    except TimeoutException:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Course Auto Register Script")
    parser.add_argument("--email", required=True, help="登入用 Email")
    parser.add_argument("--password", required=True, help="登入用密碼")
    parser.add_argument("--ocid", required=True, help="課程 OCID")
    parser.add_argument("--target_time", required=False,
                        default="11:59:55", help="目標時間 (格式 HH:mm:ss)")
    parser.add_argument("--retry", type=int, required=False,
                        default=5, help="重試次數")
    args = parser.parse_args()

    # 建立瀏覽器物件
    driver = webdriver.Chrome()

    try:
        driver.get("https://ojt.wda.gov.tw/")

        # TODO: 點擊 <button class="btn btn-info btn-info-Confirm">確定</button>
        check_information(driver=driver)

        # 登入帳號
        login(driver, email=args.email, password=args.password)

        # TODO: 點擊 <button class="btn btn-info btn-info-Confirm">確定</button>
        check_information(driver=driver)

        # 等待到 target_time 之後再進行課程報名
        register_course(target_time=args.target_time,
                        driver=driver, ocid=args.ocid)

    except Exception as e:
        print(f"Exception: {e}")

    finally:
        # 結束瀏覽器
        driver.quit()
