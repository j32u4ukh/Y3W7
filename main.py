from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time


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


def register_course(driver, ocid: str):
    URL = f"https://ojt.wda.gov.tw/ClassSearch/Detail?PlanType=1&OCID={ocid}"
    print(f"URL: {URL}")

    driver.get(URL)
    wait = WebDriverWait(driver, TIMEOUT)

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


if __name__ == "__main__":
    driver = webdriver.Chrome()
    login(driver, "email", "password")
    register_course(driver, ocid="ocid")
    driver.quit()

