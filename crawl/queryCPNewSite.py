import os,sys,csv,time,math,random,re
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

import xlrd

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.keys import Keys


outputFileName = "rejectedPaternes.csv"

def waitQueryOver(driver, tips):
    before = random.randint(9,20)
    ColorLog.info("%s sleep %d seconds before ..."%(tips, before))
    time.sleep(before)
    WebDriverWait(driver, 80).until(lambda d:  not d.find_element(By.CSS_SELECTOR, "div.q-drawer-container div.fullscreen").is_displayed() if d.find_element(By.CSS_SELECTOR, "div.q-drawer-container div.fullscreen") else True)
    post = 1
    ColorLog.info("%s sleep %d seconds post ..."%(tips,post))
    time.sleep(post)


def switchToMaxPageSize(driver):
    ColorLog.info("switch to max pagesize ...")
    driver.find_elements(By.CSS_SELECTOR, "div.table div.col-auto label")[-1].click()
    WebDriverWait(driver, 3).until(lambda d: d.find_element(By.CSS_SELECTOR, "div[role=listbox] div[role=option]").is_displayed())
    pageSizeOptions = driver.find_elements(By.CSS_SELECTOR, "div[role=listbox] div[role=option]")
    ColorLog.info("use the max pagesize,options len: %d"%len(pageSizeOptions))
    pageSizeOptions[-1].click()
    waitQueryOver(driver, "switchToMaxPageSize")

def switchToInventionOption(driver):
    ColorLog.info("switch to inverion option ...")
    driver.find_elements(By.CSS_SELECTOR, "div.search-area label.q-select")[0].click()
    WebDriverWait(driver, 3).until(lambda d: d.find_element(By.CSS_SELECTOR, "div[role=listbox] div[role=option]").is_displayed())
    patentOptions = driver.find_elements(By.CSS_SELECTOR, "div[role=listbox] div[role=option]")
    ColorLog.info("use the inverion options len: %d"%len(patentOptions))
    patentOptions[1].click()


switchToMaxPageSize.adjusted = False

def queryPerson(driver, total, company):
    driver.execute_script("document.querySelector('div[role=tabpanel] .row label span').innerText='发明专利'")
    # 导航区
    navBtns =driver.find_elements(By.CSS_SELECTOR, "div.q-pagination Button.q-btn")
    previousBtn = navBtns[0]
    nextBtn = navBtns[-1]

    inputFields = driver.find_elements(By.CSS_SELECTOR, "div[role=tabpanel] input[type=text]")
    applicant = inputFields[2]

    applicant.send_keys(32*Keys.BACKSPACE)
    applicant.send_keys(company)

    btnEles = driver.find_elements(By.CSS_SELECTOR, "div[role=tabpanel] button")
    queryBtnEle = btnEles[0]
    queryBtnEle.click()

    ColorLog.info("wait btn clickable after query %s submited  ..."%company)

    # 查询等待
    waitQueryOver(driver, "query company:%s submit"%company)

    totalNum = int(driver.find_element(By.CSS_SELECTOR, "div.total strong").text)
    ColorLog.info("company: %s has items: %d ..."%(company, totalNum))

    if not switchToMaxPageSize.adjusted:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        switchToMaxPageSize(driver)
        switchToMaxPageSize.adjusted = True
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

    # 数据区
    now                 = datetime.now()
    nowStr              = now.strftime("%Y-%m-%d")
    fourYeasAgo         = now - relativedelta(years=4)
    fourYeasAgoStr      = fourYeasAgo.strftime("%Y-%m-%d")
    ColorLog.info("now: %s, fourYeasAgo: %s ..."%(nowStr, fourYeasAgoStr))

    while True:
        continueRunning = True
        datas = driver.find_elements(By.CSS_SELECTOR, "div.tableList div.col-12")
        #ColorLog.debug("can you see data ... %d"%len(datas))
        for item in datas:
            infos = item.find_elements(By.CSS_SELECTOR, "div.table_info span")

            data = {
                    'no':       infos[1].text, 
                    'name':     infos[3].text,
                    'person':   infos[6].text,
                    'date':     infos[10].text,
                    'status':   infos[18].text
                   }

            for key, value in data.items():
                split = '：'
                pos = value.find(split)
                #ColorLog.warning("pos: %d"%pos)
                if pos != -1:
                    data[key] = value[pos + 1:].strip()

            ColorLog.debug("raw patent data: %s\napply date: %s\ntool old threshhold: %s"%(data, data['date'],fourYeasAgoStr))
            if data['date'] < fourYeasAgoStr:
                ColorLog.warning("reach the max old date threshhold: %s"%data['date'])
                continueRunning = False
                break

            status = data['status']
            if status.find("中通") != -1 or status.find("一通") != -1 or status.find("驳回等复审") != -1:
                ColorLog.warning("has a matched patent data: %s\napply date: %s\ntool old threshhold: %s"%(data, data['date'],fourYeasAgoStr))
                total.append(data)
            else:
                pass
                #total.append(data)

        if not continueRunning:
            ColorLog.notice("finish query data for person:%s for encountering too old data ..."%company)
            break

        if nextBtn.is_enabled():
            nextBtn.click()
            waitQueryOver(driver, "navigate to next page for company:%s"%company)
        else:
            ColorLog.notice("finish query data for person:%s"%company)
            break

def getInputPersonsFromExcel():
   workbook  = xlrd.open_workbook(u'有发明公司.xls')  # 打开工作簿
   sheets    = workbook.sheet_names()  # 获取工作簿中的所有表格
   worksheet = workbook.sheet_by_name(sheets[0])  # 获取工作簿中所有表格中的的第一个表格
   rows      = worksheet.nrows  # 获取表格中已存在的数据的行数
   
   persons   = []
   for row in range(1, rows):
      person  = worksheet.cell_value(row, 0).strip()
      persons.append(person)
   
   return persons

def writeRejectedPaternesToCSV(rejectedPaternes, outputFileName):
 
    if not rejectedPaternes:
        return 

    header_list = ["申请号", "专利名称", "公司名称", "状态", "申请时间"]

    with open(outputFileName, mode="w", encoding="utf-8", newline="") as fp:
       writer = csv.writer(fp)
       writer.writerow(header_list)
       writer.writerows([[x['no'], x['name'], x['person'], x['status'], x['date'] ] for x in rejectedPaternes])


if __name__ == '__main__':

    parentDirPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not parentDirPath in sys.path:
      sys.path.append(parentDirPath)

# 加载自身模块代码
from crawl.colorlog import ColorLog

# 进入主程序处理
if __name__ == '__main__':
    ColorLog.notice("begin to test, firstly test output csv file: %s can be writed ..."%outputFileName)

    with open("rejectedPaternes.csv", mode="w", encoding="utf-8", newline="") as fp:
        pass

    # 实例化对象
    options = webdriver.FirefoxOptions()
    options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    if not os.path.exists(options.binary_location):
        ColorLog.warning("Firefox binary_location does not exists in prefered path: %s"%options.binary_location)
        options.binary_location = "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
        if not os.path.exists(options.binary_location):
            ColorLog.notice("Firefox binary_location does not exists: %s"%options.binary_location)
            sys.exit(1)

    ColorLog.warning("begin to test, using Firefox binary_location: %s"%options.binary_location)


    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1440, 900)

    ColorLog.warning("begin to open main page ...")

    driver.get('https://cpquery.cponline.cnipa.gov.cn/')


    ColorLog.info("wait the main page shown ...")
    WebDriverWait(driver, timeout=60).until(lambda d: d.find_element(By.CSS_SELECTOR, "input[type=text].el-input__inner"))


    name_ele = driver.find_element(By.CSS_SELECTOR, "input[type=text].el-input__inner")
    passwordEle = driver.find_element(By.CSS_SELECTOR, "input[type=password].el-input__inner")

    # 敏感信息
    name_ele.send_keys("440823199107056233")
    passwordEle.send_keys("AIyi1314**")

    loginBtnEle = driver.find_element(By.CSS_SELECTOR, "button.login-btn")
    loginBtnEle.click()

    WebDriverWait(driver, timeout=120).until(lambda d: d.find_element(By.CSS_SELECTOR, "div[role=tabpanel] input[type=text]"))
    time.sleep(random.randint(3,6))

    WebDriverWait(driver, timeout=12).until(lambda d: d.find_element(By.CSS_SELECTOR, "div.forget-sure-u button").is_displayed())


    confirmBtnEle = driver.find_element(By.CSS_SELECTOR, "div.forget-sure-u button")

    if confirmBtnEle and confirmBtnEle.is_displayed():
        confirmBtnEle.click()
        time.sleep(1)

    ColorLog.notice("open website successfully  ...")

    
    rejectedPaternes = []
    try:
        switchToInventionOption(driver)
        company_names    = getInputPersonsFromExcel()
        for company in company_names:
            queryPerson(driver, rejectedPaternes, company)
    finally:
        writeRejectedPaternesToCSV(rejectedPaternes, outputFileName);
        driver.close()
    
    print("\r\n")
    ColorLog.notice("Has finish crawl! Please enter any key to exit:")
    input("\r\n\r\n")
    

    