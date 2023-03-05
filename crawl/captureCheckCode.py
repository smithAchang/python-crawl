import os,sys,time,random,logging,csv
import xlrd
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta



from selenium.webdriver import ChromeOptions
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder

import threading,winsound

if __name__ == '__main__':

    parentDirPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not parentDirPath in sys.path:
      sys.path.append(parentDirPath)

# 加载自身模块代码
from crawl.db import MyDB
from crawl.colorlog import ColorLog
import crawl.config as config
import crawl.recognize as Recognize
import crawl.queryCp as QueryCp


'''
  抓图主程序
'''


if __name__ == '__main__':

    mydb   = MyDB()
    myai   = Recognize.RecognizeDigitCheckCode()

    ColorLog.notice("begin to test, firstly test output csv file and db can be writed ...")


    with open("rejectedPaternes.csv", mode="w", encoding="utf-8", newline="") as fp:
        pass

    mydb.createTables()


    options = ChromeOptions()

    options.add_experimental_option('excludeSwitches', ['enable-automation'])# 开启实验性功能
    options.add_experimental_option('prefs', {"credentials_enable_service": False, "profile.password_manager_enabled": False}) # 不提示保存密码


    options.add_argument("--disable-blink-features=AutomationControlled") # 去除特征值

    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36')


    # 代理设置

    #options.add_argument("--proxy-server=http://192.168.31.217:3128")


    # 实例化谷歌
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1440, 900)

    ColorLog.info("open local db ...")    
   

    # 修改get方法
    script = '''object.defineProperty(navigator,'webdriver',{undefinedget: () => undefined})'''
    #execute_cdp_cmd用来执行chrome开发这个工具命令
    #driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",{"source": script})


    def webdriver_closed(driver):
        return driver.execute_script("return !window.navigator.webdriver")

    ColorLog.info("test windows webdriver exist ...")
    WebDriverWait(driver, timeout=60).until(webdriver_closed)

   

    try:

        ColorLog.info("begin to open main page ...")
        driver.get('http://cpquery.cnipa.gov.cn/')

        selectyzm_text_el = WebDriverWait(driver, timeout=260).until(lambda d: d.find_element(By.ID, "selectyzm_text"))
        ColorLog.info("has find yzm button ...")


        WebDriverWait(driver, timeout=160).until(lambda d: d.find_element(By.ID, "selectyzm_text").text.startswith('请依次点击'))
        ColorLog.info('element content:' + selectyzm_text_el.text)

        ColorLog.info("enter login username ...")

        username_input_el = driver.find_element(By.ID, "username1")
       
        username_input_el.send_keys(config.__PATERN_LOGIN_USER_NAME__)

        password_input_el = driver.find_element(By.ID, "password1")
        password_input_el.send_keys(config.__PATERN_LOGIN_PASSWORD__)

        
    

        ColorLog.notice("请输入登录的图形验证码 ...")
        WebDriverWait(driver, timeout=360).until(lambda d: d.find_element(By.ID, "selectyzm_text").text.startswith('验证成功'))
        ColorLog.info("登录的图形验证码验证成功 ...")

        ColorLog.notice("登录后，确认告知书界面，请不要移动鼠标 ...")
        agreeid_radio_el = WebDriverWait(driver, timeout=260).until(lambda d: d.find_element(By.ID, "agreeid"))
        go_button_el     =  driver.find_element(By.ID, "goBtn")

        ActionChains(driver).move_to_element(agreeid_radio_el).click().move_to_element(go_button_el).click().perform()


        #query_button_el      = driver.find_element(By.ID, "query")
        ColorLog.info("请等待进入查询专利页面 ...")
        WebDriverWait(driver, timeout=360).until(lambda d: d.find_element(By.CSS_SELECTOR, ".welcome"))
        ColorLog.notice("进入查询专利页面 ...")

        authImg_ele =  driver.find_element(By.ID, "authImg")
        homePath    = os.path.join(os.getcwd(), 'authImg') 

        home,dirs,files = next(os.walk(homePath))
        beginNo         = len(files)

        ColorLog.notice("begin to loop ...")

        person_input_ele = driver.find_element(By.ID, "select-key:shenqingrxm")
        person_input_ele.clear()
        person_input_ele.send_keys('广东鑫光智能系统有限公司')

        for i in range(1, 1024):
            pathtofile = os.path.join(homePath, "%d.png"%(i+beginNo))
            print(pathtofile)

                    
            person_input_ele = driver.find_element(By.ID, "select-key:shenqingrxm")
            person_input_ele.clear()
            person_input_ele.send_keys('广东鑫光智能系统有限公司')

            QueryCp.enterDigitCheckCodeDate(driver , myai, pathtofile)

            
            ColorLog.notice("enter key for next loop: %d ..."%i)
            wait_any_input = input()
            


    except Exception as e:
        ColorLog.error(e)

    finally:

        if mydb:
            mydb.closeDB()
                
        driver.quit()

        # 获取输入结束
        threading._start_new_thread (QueryCp.beep, ((1000,2000,4000),), {'loop': 65535} )
        ColorLog.critical("exit from main ; input any key plus enter key to exit from program !!!")
        wait_any_input = input()
