import undetected_chromedriver as uc

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.keys import Keys

import time
import logging


# 实例化对象
logging.basicConfig(format="%(asctime)s %(message)s")
logging.warning("begin to test ...")


driver = webdriver.Firefox()
driver.set_window_size(1440, 900)



logging.warning("begin to open main page ...")

driver.get('https://cpquery.cponline.cnipa.gov.cn/')


logging.info("test windows webdriver exist ...")
WebDriverWait(driver, timeout=60).until(lambda d: d.find_element(By.CSS_SELECTOR, "input[type=text].el-input__inner"))


name_ele = driver.find_element(By.CSS_SELECTOR, "input[type=text].el-input__inner")

name_ele.send_keys("440823199107056233")


passwordEle = driver.find_element(By.CSS_SELECTOR, "input[type=password].el-input__inner")
passwordEle.send_keys("AIyi1314**")

loginBtnEle = driver.find_element(By.CSS_SELECTOR, "button.login-btn")

loginBtnEle.click()

WebDriverWait(driver, timeout=120).until(lambda d: d.find_element(By.CSS_SELECTOR, "div[role=tabpanel] input[type=text]"))
WebDriverWait(driver, timeout=12).until(lambda d: d.find_element(By.CSS_SELECTOR, "div.forget-sure-u button").is_displayed())


confirmBtnEle = driver.find_element(By.CSS_SELECTOR, "div.forget-sure-u button")

if confirmBtnEle and confirmBtnEle.is_displayed():
    confirmBtnEle.click()
    time.sleep(1)

inputFields = driver.find_elements(By.CSS_SELECTOR, "div[role=tabpanel] input[type=text]")

applicant = inputFields[2]


logging.warning("open successfully  ...")

typeSpanEle= driver.find_element(By.CSS_SELECTOR, "div[role=tabpanel] .row label span")

driver.execute_script("document.querySelector('div[role=tabpanel] .row label span').innerText='发明专利'")
driver.execute_script("document.querySelector('main div.justify-center.items-center label span').innerText='50'")


applicant.send_keys(32*Keys.BACKSPACE)
applicant.send_keys(u'广东鑫光智能系统有限公司')

btnEles = driver.find_elements(By.CSS_SELECTOR, "div[role=tabpanel] button")
queryBtnEle = btnEles[0]
queryBtnEle.click()

len(driver.find_elements(By.CSS_SELECTOR, "div[role=tabpanel] .q-field__control-container"))

len(driver.find_elements(By.CSS_SELECTOR, "main div.search-area div.tableList div.table"))

time.sleep(360)
driver.close()

    