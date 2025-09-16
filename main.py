import argparse
import datetime
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


TIMEOUT = 20  # 等待元素最大秒數


def login(driver, email: str, password: str):
    URL = "https://ojt.wda.gov.tw/"
    driver.get(URL)
    wait = WebDriverWait(driver, TIMEOUT)

    # 點擊會員登入
    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/Member/Login']"))).click()
    print("Click login button")

    # 輸入帳號密碼
    wait.until(EC.presence_of_element_located((By.ID, "CPH1_txt_EmailId"))).send_keys(email)
    wait.until(EC.presence_of_element_located((By.ID, "CPH1_txt_dwsp"))).send_keys(password)

    # 處理驗證碼 (iframe)
    captcha_code = input("captcha_code: ")
    print(f"captcha_code: {captcha_code}")

    # 切回主頁填寫驗證碼
    driver.switch_to.default_content()
    wait.until(EC.presence_of_element_located((By.ID, "CPH1_txt_VerifyCode"))).send_keys(captcha_code)

    # 點擊登入
    wait.until(EC.element_to_be_clickable((By.ID, "CPH1_btnLogin"))).click()
    print("完成登入!!")


def register_course(target_time: str, driver, ocid: str):
    URL = f"https://ojt.wda.gov.tw/ClassSearch/Detail?PlanType=1&OCID={ocid}"
    print(f"URL: {URL}")

    driver.get(URL)
    wait = WebDriverWait(driver, TIMEOUT)
    
    # 給定指定時間 HH:mm:ss，這個時間前，間隔 10 毫秒或 100 毫秒檢查一次，時間到了再繼續執行
    if target_time is not None:
        wait_until(target_time=target_time, 
                   threshold1=10, interval1=5, 
                   threshold2=1.5, interval2=1,
                   threshold3=0, interval3=0.1)

    # 等待「我要報名」按鈕並點擊
    enroll_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[@data-role='EnterClass' and normalize-space(text())='我要報名']")
        )
    )
    enroll_button.click()
    print("Click EnterClass button")

    # 等待「報名」按鈕出現並點擊
    # <button type="button" data-role="GoSignUp" class="btn-orange" title="報名">報名</button>
    go_sign_up_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[@data-role='GoSignUp' and normalize-space(text())='報名']"))
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
        EC.element_to_be_clickable((By.XPATH, "//button[@data-role='SaveData' and @title='送出報名資料']"))
    )
    submit_button.click()
    
    # <button class="btn btn-info btn-info-Confirm">確定</button>
    # 等待彈出視窗，點擊「確定」
    confirm_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'btn-info-Confirm') and normalize-space(text())='確定']"))
    )
    driver.execute_script("arguments[0].click();", confirm_btn)
    print("Click confirm button on popup")

    """
    <h3 class="main-title main-title-blue"><i class="fas fa-edit space-right"></i>課程報名結果</h3>
    """
    # 等待課程報名結果頁面元素出現，確保報名成功
    result_title = WebDriverWait(driver, TIMEOUT * 3).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h3[contains(@class,'main-title') and contains(text(),'課程報名結果')]")
        )
    )
    print("課程報名完成，已出現報名結果頁面")


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
        print(f"Now: {now}, delta: {delta}")

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


if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description="Course Auto Register Script")
    parser.add_argument("--email", required=True, help="登入用 Email")
    parser.add_argument("--password", required=True, help="登入用密碼")
    parser.add_argument("--ocid", required=True, help="課程 OCID")
    parser.add_argument("--target_time", required=True, help="目標時間 (格式 HH:mm:ss)")
    args = parser.parse_args()

    # 建立瀏覽器物件
    driver = webdriver.Chrome()

    # 登入帳號
    login(driver, email=args.email, password=args.password)

    # 等待到 target_time 之後再進行課程報名
    register_course(target_time=args.target_time, driver=driver, ocid=args.ocid)

    # 結束瀏覽器
    driver.quit()

