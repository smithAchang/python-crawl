import os,sys,time,random,logging,csv,re
import math,random
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


'''
  爬虫主程序
'''

__VERSION__ = "V1.6.6"

# 类定义
class NoQueryResultError(Exception):
    pass


# 方法区
def EnterAnyKeyWhenOK(tips):
    ColorLog.warning(tips)
    input()

# 声音警报
def beep(durations=(1000,2000,4000), loop=1):
    loop *= len(durations)
    #print(loop)
    while loop > 0 :
        for seconds in durations:
            #print(seconds)
            time.sleep(1)
            winsound.Beep(3000, seconds)
            if loop < 65535 :
                loop -= 1

def LoopWaitCondition(driver, condition, tips, specialTipPrint=None):
    beepCount = 0

    while True:
        try:
            WebDriverWait(driver, timeout=15).until(condition)
            ColorLog.info("has meet condition for %s"%tips)
            break
        except NoQueryResultError as e:
            ColorLog.warning("the customized error can not be raised out")
            break
        except Exception as e:
            #print(e)
            ColorLog.warning("loop wait timeout for %s"%tips)
            if specialTipPrint:
                ColorLog.notice(specialTipPrint)
                beep()
                beepCount = 0
        finally:
            beepCount +=  1
            if beepCount >= 10:
                beep()
                beepCount = 0


def WaitPaternListHasData(driver, timeout=None):

    inner_timeout = 0

    def hasResultsOrNoResults(d):
        
        nonlocal inner_timeout
        
        notify_empty        = None

        if timeout :
            inner_timeout       += 1
            if inner_timeout >= timeout :
                ColorLog.warning("WaitPaternListHasData timeout: %d ..."%timeout)
                return "timeout"


        # 部分情况处理，如果遇到特殊判断加try/catch，不然，后面常态有数据列表就无法判断
        try:
            notify_empty = d.find_element(By.CSS_SELECTOR, ".empty_date")
        except Exception as e:
            pass

        if notify_empty:
            ColorLog.warning("WaitPaternListHasData notify_empty ...")
            return notify_empty
       
        ColorLog.info("WaitPaternListHasData to find content listx...")     
        return d.find_element(By.CSS_SELECTOR, ".content_listx")
      
    
    LoopWaitCondition(driver, hasResultsOrNoResults, 'hasQueryContent')
    
    # double check to produce the real result
    notify_empty = None
      
    try:
       notify_empty = driver.find_element(By.CSS_SELECTOR, ".empty_date")
       ColorLog.warning("secial case, has found empty result notify !")
    except Exception as e:
           pass

       
    if notify_empty:
       return "nodata"

    if timeout and inner_timeout >= timeout:
       return "timeout"


    return "got"




def getContentList(driver):
    
    NO_eles      =  driver.find_elements(By.CSS_SELECTOR, ".content_listx_patent tr td:nth-child(2)")
    NAME_eles    =  driver.find_elements(By.CSS_SELECTOR, ".content_listx_patent tr td:nth-child(3)")
    PERSON_eles  =  driver.find_elements(By.CSS_SELECTOR, ".content_listx_patent tr span[name='record:shenqingrxm']")
    PUBLISH_eles =  driver.find_elements(By.CSS_SELECTOR, ".content_listx_patent tr span[name='record:shouquanggr']")
    result       = []

    ColorLog.info("get patern content list len: %d..."%len(NO_eles))

    for i, v in enumerate(NO_eles):
      result.append((NO_eles[i].text, NAME_eles[i].text, PERSON_eles[i].text, PUBLISH_eles[i].text))
      ColorLog.info(str(result[i]))

    
    return result

def searchEveryContentPages(driver, historyRejectedPaternes, totalPages):
     for page in range(1, totalPages + 1):

        ColorLog.info("analyse the content in page %d , first navigate to the page to avoid input checkcode again..."%page)
        pageNo_input_ele = driver.find_element(By.CSS_SELECTOR, ".pagination li input.form-control")
        pageNo_input_ele.clear()
        # 4*Keys.BACKSPACEstr
        pageNo_input_ele.send_keys( str(page) + Keys.ENTER)

        sleepDelay = random.randint(config.__COMMON_NAVIGATE_PAGE_MIDDLE_SLEEP_MIN__, config.__COMMON_NAVIGATE_PAGE_MIDDLE_SLEEP_MAX__)
        ColorLog.info("analyse the content in page %d , wait for %d seconds..."%(page, sleepDelay))
        time.sleep(sleepDelay)
       
        paterns               = getContentList(driver)
        onePageRejectedResult = searchContentListForRejected(driver, mydb, paterns, (page, totalPages))

        if onePageRejectedResult :
            ColorLog.info("find rejected_paterns num: %d ..."%len(onePageRejectedResult))
            historyRejectedPaternes.extend(onePageRejectedResult)

def enterApplyDate(driver):
    now                 = datetime.now()
    nowStr              = datetime.strftime(now, "%Y-%m-%d")
    fourYeasAgo         = now - relativedelta(years=4)
    queryBeginDateStr   = "{}-{}-{}".format(fourYeasAgo.year, fourYeasAgo.month, fourYeasAgo.day)
    applyDate_input_ele = driver.find_element(By.ID, "select-key:shenqingr_from")
    verycode_input_ele  = driver.find_element(By.ID, "very-code")


    applyDate_input_ele.clear()
    applyDate_input_ele.send_keys(queryBeginDateStr)

    ActionChains(driver).move_to_element(applyDate_input_ele).double_click().pause(1).perform()
    
    # 跨了iframe
    calendar_iframe = driver.find_elements(By.TAG_NAME, 'iframe')
    ColorLog.info('calendar_iframe is second : %d'%len(calendar_iframe))
    driver.switch_to.frame(1)
    dateOK_ele      = driver.find_element(By.ID, 'dpOkInput')
    ActionChains(driver).move_to_element(dateOK_ele).click().pause(1).perform()
    driver.switch_to.default_content()

def enterDigitCheckCodeDate(driver, ai, pathtofile):

    while True:
        authImg_ele         = driver.find_element(By.ID, "authImg")
        base64_str          = authImg_ele.screenshot_as_base64
        result              = ai.predictImgBase64Str(base64_str)
        ColorLog.notice("get result : %d ..."%result)

        verycode_input_ele  = driver.find_element(By.ID, "very-code")
        submit_query_ele    = driver.find_element(By.ID, "query")

        ActionChains(driver).move_to_element(verycode_input_ele).click_and_hold().send_keys(str(result)).pause(2).move_to_element(submit_query_ele).click().pause(1).perform()
        ColorLog.info("WaitPaternListHasData after entered digit checkcode result : %d ..."%result)
        waitResult          = WaitPaternListHasData(driver, timeout=60)
        
        if waitResult != "timeout":
            break
        else:
            ColorLog.notice("爬虫智能自动输入数字验证可能存在错误，请检查! 谢谢 !!!")
            beep()

    return waitResult

def enterLoginCheckCode(driver):

    ColorLog.info("hover chinese text button to show checkcode image ...")
    chinese_checkcode_ele = driver.find_element(By.ID, "selectyzm_text")
    loginBtn_ele          = driver.find_element(By.ID, "publiclogin")
    image_checkcode_ele   = driver.find_element(By.ID, "jcaptchaimage")

    ActionChains(driver).move_to_element(chinese_checkcode_ele).perform()

    time.sleep(2)
    ColorLog.info("wait chinese checkcode to display ...")
    
    WebDriverWait(driver, timeout=160).until(lambda d: image_checkcode_ele.is_displayed())

    beginNo                     = None
    pathtoChineseCheckcodeFile  = None
    captureChineseCheckCodeHome = os.path.join('.', 'login')

    if os.path.exists(captureChineseCheckCodeHome):
        home,dirs,files = next(os.walk(captureChineseCheckCodeHome))
        beginNo         = len(files)

    
    imageRect     = image_checkcode_ele.rect.copy()
    width         = imageRect['width']
    height        = imageRect['height']
    center_x      = int(width/2)
    center_y      = int(height/2)


    ColorLog.info('image_checkcode_ele rect : {}'.format(imageRect))

    checkcodeText = chinese_checkcode_ele.text
    base64_str    = driver.get_screenshot_as_base64()
    
    i             = 0
    while i < 53:
        i += 1
        newCheckcodeText = chinese_checkcode_ele.text
        
        if newCheckcodeText != checkcodeText :
            ColorLog.info('has new checkcode image, show it to capture for %d times ... '%i)
            ActionChains(driver).move_to_element(chinese_checkcode_ele).pause(1).perform()
            time.sleep(1)
            checkcodeText = newCheckcodeText
            base64_str    = driver.get_screenshot_as_base64()
        
        
        ColorLog.notice('checkcodeTextes: {} for {} times'.format(checkcodeText, i))
        matched       = re.match(r'.+?"(.)"\s+"(.)"\s+"(.)"', checkcodeText)
        if beginNo != None:
            pathtoChineseCheckcodeFile    = os.path.join(captureChineseCheckCodeHome, 'chinese%d.png'%(beginNo + i))

  
        history       = set()
        needRecognizedChineses = matched.groups()

        for charindex, checktext in enumerate(needRecognizedChineses) :
            
            pos = Recognize.recognizeChineseCharBase64(base64_str, imageRect, checktext, pathtoChineseCheckcodeFile)
            if pos not in history:
                distance = [math.dist(x, pos) for x in history]

                if len(distance) > 0 and min(distance) < 25 :
                    ColorLog.warning("history has near pos: {}, history: {}, distance: {}".format(pos, history, distance))
                    # 左上区域不能点击
                    pos = (random.randint(1, width - 30), random.randint(1, height - 30))

                
            else:
                ColorLog.warning("has old pos {} in history {}".format(pos, history))
                pos = (random.randint(1, width - 30), random.randint(1, height - 30))

            history.add(pos)

            
            
            ColorLog.info('NO.{} checktext: {}, pathtoChineseCheckcodeFile: {}, click_pos: {}, imageCenter_x: {}, imageCenter_y: {}'.format(charindex, checktext, pathtoChineseCheckcodeFile, pos, center_x, center_y))
      
            # 自动化时图片一直点击会出现错误，要循环打开
            ActionChains(driver).move_to_element(chinese_checkcode_ele).click().pause(1).move_to_element_with_offset(image_checkcode_ele, pos[0] - center_x, pos[1] - center_y).click().pause(1).move_to_element(loginBtn_ele).pause(1).perform()

            # 某些情况图片已经替换，还在继续比对是不正确的，要及时跳出循环
            newCheckcodeText = chinese_checkcode_ele.text
            if  charindex < (len(needRecognizedChineses) - 1) and newCheckcodeText != checkcodeText :
                ColorLog.warning("auth chinese input in failure %d times; oldCheckcodeText: %s ,newCheckcodeText: %s !"%(i, checkcodeText, newCheckcodeText))

                break
      
        
        if chinese_checkcode_ele.text.startswith('验证成功'):
            ColorLog.notice("has recognize successfuly after %d times !"%i)
            break

        if chinese_checkcode_ele.text.startswith('失败过多'):
            ColorLog.notice("has failed %d  many times!"%i)
            chinese_checkcode_ele.click()
            time.sleep(random.randint(2, 8))
        else:
            ColorLog.info("enter chinese checkcode in failure %d times, sleep a while ... "%i)
            time.sleep(2)
            #ColorLog.notice("enter any key to continue ...")
            #wait_any_input = input() 






def searchContentListForRejected(driver, mydb, paterns, pageinfo):
    
    rejectedPaterns = []

    for i, patern in enumerate(paterns):

      patern_no      = patern[0]
      patern_name    = patern[1]
      patern_person  = patern[2]
      publish_date   = patern[3]

      pageInidi      = "{}/{}".format(pageinfo[0], pageinfo[1])

      
      ColorLog.info("analyse page: %s , index: %d,  NO: %s, NAME: %-24s, PERSON: %-24s, PUBLISH_DATE: %s"%(pageInidi, i, patern_no, patern_name, patern_person, publish_date))

      
      if publish_date != '':
        ColorLog.info("analyse page: %s , index: %d, NO: %s has publish date at %s , no need to crawl ! "%(pageInidi, i, patern_no, publish_date))
        continue

      if mydb.isPaternRejected(patern_no):
        ColorLog.info("analyse page: %s , index: %d, NO: %s has rejected before and no need to be crawled ! "%(pageInidi, i, patern_no))
        continue

      # 需要等待元素产生，不使用睡眠机制
      conversation_link_eles          = WebDriverWait(driver, timeout=60).until(lambda d: d.find_elements(By.CSS_SELECTOR, ".content_boxx ul li:nth-child(4) a"))  

      ColorLog.info("analyse page: %s , index: %d, NO: %s has no publish date, so see conversion information, click it "%(pageInidi, i, patern_no))
    
      conversation_link_eles[i].click()
      
      sleepDelay = random.randint(config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MIN__, config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MAX__)
      ColorLog.info("analyse page: %s , index: %d, NO: %s sleep %d to show conversation page information"%(pageInidi, i, patern_no, sleepDelay))
      time.sleep(sleepDelay)

      LoopWaitCondition(driver, lambda d: d.find_element(By.ID, "fwid"), "toFindConversionList")

      conversation_eles         =  driver.find_elements(By.CSS_SELECTOR, "#fwid span[name='record_fawen:tongzhislx'")
      conversation_date_eles    =  driver.find_elements(By.CSS_SELECTOR, "#fwid span[name='record_fawen:fawenrq'")

      for j, conversation in  enumerate(conversation_eles):

        now               = datetime.now()
        nowStr            = datetime.strftime(now, "%Y-%m-%d")
        conversation_date = conversation_date_eles[j].get_attribute('title')

        ColorLog.info("analyse page: %s , index: %d, NO: %s converstion : %-24s at date: %s"%(pageInidi, i, patern_no, conversation.text, conversation_date))

        if conversation.text.find(u"撤回通知书") != -1 :
            ColorLog.info("analyse page: %s , index: %d, find NO: %s is recalled at %s . The apply flow is end !"%(pageInidi, i, patern_no, conversation_date))
            break

        if conversation.text.find(u"驳回决定") != -1 :
            ColorLog.info("analyse page: %s , index: %d, find NO: %s is rejected at %s !"%(pageInidi, i, patern_no, conversation_date))
            rejected_date = conversation_date
        
            threemonthago    = now - timedelta(days=90)
            threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")
            if rejected_date > threemonthagoStr:
                ColorLog.notice("analyse page: %s , index: %d, find rejected NO: %s is not beyond the date threshhold at %s !"%(pageInidi, i, patern_no, conversation_date))
                mydb.modRejectedPatern(patern_no, patern[1], patern[2], rejected_date)
                rejectedPaterns.append((patern, rejected_date))

            # 按照第一次驳回决定来    
            break

        if conversation.text.find(u"审查意见通知书") != -1 :
            ColorLog.info("analyse page: %s , index: %d, find NO: %s has office action at %s !"%(pageInidi, i, patern_no, conversation_date))
            mydb.modWaitQueryAgainPatern(patern_no, patern_name, patern_person, conversation_date, nowStr)        
            break

      
      driver.back()

      sleepDelay = random.randint(config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MIN__, config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MAX__)  
      ColorLog.notice("analyse page: %s , index: %d, NO: %s has seen all conversationes and will navigate back to query content list again %d seconds lately ..."%(pageInidi, i, patern_no, sleepDelay))
      time.sleep(sleepDelay)
    

    ColorLog.info("finish process content list")
    return rejectedPaterns


def writeRejectedPaternesToCSV(rejectedPaternes, fromDB=True):
 
    if not rejectedPaternes:
        return 

    header_list = ["申请号", "专利名称", "公司名称", "驳回时间"]


    with  open("rejectedPaternes.csv", mode="w", encoding="utf-8", newline="") as fp:
       writer = csv.writer(fp)
       writer.writerow(header_list)

       if fromDB:
         writer.writerows([list(x) for x in rejectedPaternes])
       else:
         writer.writerows([ [x[0][0], x[0][1], x[0][2], x[1] ] for x in rejectedPaternes])

def queryDataFinishRefreshThePage(driver, i, qeuryData):
        ColorLog.warning("requet fresh page and clear current {} query content to enter next loop ...".format(qeuryData))

        ActionChains(driver).move_to_element(driver.find_element(By.ID, "header_query")).click().perform()
        LoopWaitCondition(driver, lambda d: len(driver.find_element(By.ID, "select-key:shenqingrxm").text) == 0, 'personInputCleared')
        
        sleepDelay = random.randint(config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MIN__, config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MAX__)
        ColorLog.warning("finish %d loop and sleep for %d seconds lately !!\r\n\r\n"%(i, sleepDelay))
        time.sleep(sleepDelay)

def queryPersones(driver, mydb, persones):

    all_person_rejected_paternes = []

    for i, person in enumerate(persones):

        ColorLog.info("begin loop: %d new analyse patern list for %s . clear old running data firstly"%(i, person))

        mydb.deleteOldData()


        if mydb.isCompanyHasBeenQueryed(person):
            ColorLog.info("%s has been analysed today !"%person)
            continue

        ColorLog.info("enter person name: %s"%person)  
        person_input_ele = driver.find_element(By.ID, "select-key:shenqingrxm")
        person_input_ele.clear()
        person_input_ele.send_keys(person)
          
        ColorLog.info("enter invention patern type for %s"%person)  
        ActionChains(driver).move_to_element(driver.find_element(By.ID, "select-key:zhuanlilx")).click().pause(1).perform()
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "p.bs_l_r:nth-child(1)")).click().perform()

        ColorLog.info("enter four year threshhold for filing date for %s"%person)  
        enterApplyDate(driver)
        
          
        ColorLog.info("ai enter digit checkcode to query result for %s"%person)  
        isHasResult       = enterDigitCheckCodeDate(driver, myai, 'digit_checkcode.png')

        if isHasResult == "nodata" :
            mydb.modCompanyQuueryStatus(person ,'finished')
            ColorLog.warning("%s has no any record, please check input conditions!"%person)
            queryDataFinishRefreshThePage(driver, i, person)
            continue

        ColorLog.info("query total pages to navigate for %s"%person)  
        pageNavigator_ele = driver.find_element(By.CSS_SELECTOR, ".pagination")
        totalPages        = int(pageNavigator_ele.get_attribute('data-totalpage'))

         
        ColorLog.info(" %s has %d pages results ..."%(person, totalPages))
        searchEveryContentPages(driver, all_person_rejected_paternes,  totalPages)


        ColorLog.info("set %s query finished status"%person)
        mydb.modCompanyQuueryStatus(person ,'finished')
                
        queryDataFinishRefreshThePage(driver, i, person)

    return all_person_rejected_paternes

def queryNeedQueryAgainOldPaterns(driver, mydb):

        mydb.deleteOldData()

        waitQueryAgainPaterns = mydb.getNeedQueryAgainPaternData()
        totalNeedQueryAgain   = len(waitQueryAgainPaterns)

        if totalNeedQueryAgain == 0:
            ColorLog.notice("has no any old patern data needing to be crawl again ...")
            return []

        query_again_rejected_paternes = []
        person_input_ele = driver.find_element(By.ID, "select-key:shenqingrxm")
        person_input_ele.clear()

        no_input_ele = driver.find_element(By.ID, "select-key:shenqingh")
        no_input_ele.clear()

        for i, patern in enumerate(waitQueryAgainPaterns):
            now                     = datetime.now()
            nowStr                  = datetime.strftime(now, "%Y-%m-%d")

            patern_no               = patern[0]
            patern_name             = patern[1]
            patern_person_name      = patern[2]
            createDateStr           = patern[3]
            updateDateStr           = patern[4]
            canQueryDate            = datetime.strptime(updateDateStr, "%Y-%m-%d") + timedelta(days=7)
            canQueryDateStr         = datetime.strftime(canQueryDate, "%Y-%m-%d")

            if canQueryDateStr > nowStr:
                ColorLog.info("restricted query again data running frequently. canQueryDateStr {}, nowStr {} ".format(canQueryDateStr, nowStr))
                continue

            ColorLog.info("begin loop: {}/{} process need query again old patern for {} ; enter for patern no ...".format(i, totalNeedQueryAgain, patern))
            no_input_ele = driver.find_element(By.ID, "select-key:shenqingh")
            no_input_ele.clear()
            no_input_ele.send_keys(patern_no)

            ColorLog.info("enter invention patern type for {}".format(patern))  
            ActionChains(driver).move_to_element(driver.find_element(By.ID, "select-key:zhuanlilx")).click().pause(1).perform()
            ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "p.bs_l_r:nth-child(1)")).click().perform()

            ColorLog.info("enter four year threshhold for filing date for {}".format(patern))  
            enterApplyDate(driver)

            ColorLog.info("ai enter digit checkcode to query result for {}".format(patern))  
            isHasResult       = enterDigitCheckCodeDate(driver, myai, None)

            if isHasResult == "nodata" :
                mydb.delWaitQueryAgainPaternData(patern_no)
                ColorLog.warning("{} has no any record, delete this data !".format(patern))
                queryDataFinishRefreshThePage(driver, i, patern)
                continue

            page_patern       = getContentList(driver)
            publish_date      = page_patern[0][3]

            if publish_date != '':
                ColorLog.info("NO: %s has publish date at %s , no need to keep track ! "%(patern_no, publish_date))
                mydb.delWaitQueryAgainPaternData(patern_no)
                queryDataFinishRefreshThePage(driver, i, patern)
                continue
         
            # 需要等待元素产生，不使用睡眠机制
            conversation_link_eles          = WebDriverWait(driver, timeout=60).until(lambda d: d.find_elements(By.CSS_SELECTOR, ".content_boxx ul li:nth-child(4) a"))  

            ColorLog.info("analyse wait lately query again patern data . index: %d/%d, NO: %s has no publish date, so see conversion information, click it "%(i, totalNeedQueryAgain, patern_no))
    
            conversation_link_eles[0].click()
      
            sleepDelay = random.randint(config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MIN__, config.__COMMON_NAVIGATE_PAGE_SHORT_SLEEP_MAX__)
            ColorLog.info("analyse wait lately query again patern data . index: %d/%d, NO: %s sleep %d to show conversation page information"%(i, totalNeedQueryAgain, patern_no, sleepDelay))
            time.sleep(sleepDelay)

            LoopWaitCondition(driver, lambda d: d.find_element(By.ID, "fwid"), "toFindConversionList")

            conversation_eles         =  driver.find_elements(By.CSS_SELECTOR, "#fwid span[name='record_fawen:tongzhislx'")
            conversation_date_eles    =  driver.find_elements(By.CSS_SELECTOR, "#fwid span[name='record_fawen:fawenrq'")
            hasDeleted                = False

            for j, conversation in  enumerate(conversation_eles):

                conversation_date = conversation_date_eles[j].get_attribute('title')

                ColorLog.info("analyse wait lately query again patern data . index: %d/%d, NO: %s converstion : %-24s at date: %s"%( i, totalNeedQueryAgain, patern_no, conversation.text, conversation_date))

                if conversation.text.find(u"撤回通知书") != -1 :
                    ColorLog.info("analyse wait lately query again patern data . index: %d/%d, find NO: %s is recalled at %s ,delete it for tracking !"%( i, totalNeedQueryAgain, patern_no, conversation_date))
                    mydb.delWaitQueryAgainPaternData(patern_no)
                    hasDeleted = True
                    break

                if conversation.text.find(u"驳回决定") != -1:
                    ColorLog.info("analyse wait lately query again patern data . index: %d/%d, find NO: %s is rejected at %s !"%( i, totalNeedQueryAgain, patern_no, conversation_date))
                    rejected_date = conversation_date
        
                    threemonthago    = now - timedelta(days=90)
                    threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")
                    if rejected_date > threemonthagoStr:
                        ColorLog.notice("analyse wait lately query again patern data . index: %d/%d, find rejected NO: %s is not beyond the date threshhold at %s !"%(i, totalNeedQueryAgain, patern_no, conversation_date))
                        mydb.modRejectedPatern(patern_no, patern_name, patern_person_name, rejected_date)
                        query_again_rejected_paternes.append((patern, rejected_date))

                    # 按照第一次驳回决定来
                    mydb.delWaitQueryAgainPaternData(patern_no)
                    hasDeleted = True    
                    break

            if not hasDeleted :
                ColorLog.info(" set {} has been queryed and set update_date: {} and crawl new loop ...".format(patern, nowStr))
                mydb.modWaitQueryAgainPatern(patern[0], patern[1], patern[2], patern[3], nowStr)

            queryDataFinishRefreshThePage(driver, i, patern)

        return query_again_rejected_paternes





def captureDigitCheckCode(driver, ele):

    for i in range(1, 100):
      sleepDelay = random.randint(1, 15)
      ColorLog.info("I will capture digit checkcode image %d and wait %d seconds ......."%(i, sleepDelay))
      ele.screenshot('./authImg/%d'%i + 'image.png')
      
      time.sleep(sleepDelay)
      auth_img_el          = WebDriverWait(driver, timeout=15).until(lambda d: d.find_element(By.ID, "authImg"))
        
      reset_button_el      = driver.find_element(By.ID, "reset")
      ActionChains(driver).move_to_element(reset_button_el).click().move_to_element(auth_img_el).click().pause(1).perform()

def captureLoginCheckCode(driver, ele):
      ActionChains(driver).move_to_element(selectyzm_text_el).perform()

      jcaptchaimage_el  = driver.find_element(By.ID, "jcaptchaimage")

      ColorLog.debug('visible test ...')
        
      WebDriverWait(driver, timeout=10).until(lambda d:  jcaptchaimage_el.is_displayed())
      time.sleep(1)       
    
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

        if not hasattr(config, '__LOGIN_CHECKCODE_AUTO_ENTER_IN' ) or config.__LOGIN_CHECKCODE_AUTO_ENTER_IN:
            enterLoginCheckCode(driver)
    
        if not driver.find_element(By.ID, "selectyzm_text").text.startswith('验证成功'):
            ColorLog.notice("请手工输入登录的图形验证码，验证成功后，继续点击登录按钮 ...")
            # 异步方式以利于及时判断手工输入正确，不然手速可能太快了
            threading._start_new_thread (beep, ((1000,2000,4000),), {'loop': 1} )
            WebDriverWait(driver, timeout=360).until(lambda d: d.find_element(By.ID, "selectyzm_text").text.startswith('验证成功'))
        else:
            driver.find_element(By.ID, "publiclogin").click()

        ColorLog.notice("在确认告知书界面，请不要移动鼠标! 爬虫开始自动过程 ...")
        agreeid_radio_el = WebDriverWait(driver, timeout=260).until(lambda d: d.find_element(By.ID, "agreeid"))
        go_button_el     =  driver.find_element(By.ID, "goBtn")

        ActionChains(driver).move_to_element(agreeid_radio_el).click().move_to_element(go_button_el).click().perform()


        ColorLog.info("请等待进入查询专利页面 ...")
        WebDriverWait(driver, timeout=360).until(lambda d: d.find_element(By.CSS_SELECTOR, ".welcome"))
        ColorLog.notice("进入查询专利页面 ...")

        company_names    = [u'广东鑫光智能系统有限公司', u'广东鑫光智能系统有限公司1', u'广东寻米科技有限公司']
        company_names    = [u'广东鑫光智能系统有限公司', u'广东寻米科技有限公司', u'广东鑫光智能系统有限公司1']
        company_names    = [u'广东鑫光智能系统有限公司']
        company_names    = [u'广东鑫光智能系统有限公司1', u'广东寻米科技有限公司']
        company_names    = [u'广东鑫光智能系统有限公司1', u'广东寻米科技有限公司1',  u'广东寻米科技有限公司']
        company_names    = [u'广东鑫光智能系统有限公司', u'广东寻米科技有限公司', u'广东鑫光智能系统有限公司1']
        company_names    = [u'广东寻米科技有限公司', u'广东鑫光智能系统有限公司1', u'广东鑫光智能系统有限公司']
        company_names    = [u'她力量文化科技（广州）有限公司']
        company_names    = [u'广东鑫光智能系统有限公司',u'广东鑫光智能系统有限公司1']
        company_names    = getInputPersonsFromExcel()
       
        
        ColorLog.notice("firstly crawl old patern datas with office action ...")
        special_rejected_paterns = queryNeedQueryAgainOldPaterns(driver, mydb)

        ColorLog.notice("has %d persones"%len(company_names))

        rejected_paterns = queryPersones(driver, mydb, company_names)
       
        rejected_paterns.extend(special_rejected_paterns)

        if rejected_paterns:
          ColorLog.notice("crawled all persons and has rejected paternes, total sum: %d ......."%len(rejected_paterns))
        else:
          ColorLog.warning("has crawled all persons , but has not found any rejected paternes ! Will exit !")
        
        # 正常退出
        logout_btn_ele = driver.find_element(By.ID, "navLogoutBtn")

        ActionChains(driver).move_to_element(logout_btn_ele).click().pause(1).perform()
        ActionChains(driver).move_to_element(driver.find_element(By.ID, "button-0")).click().perform()

        ColorLog.warning("logout browser normally !") 

       
        
        dataFromDB = mydb.getAllPaternRejectedData()
        ColorLog.notice("query data from db and write rejectedPaternes csv file, total sum: %d .  ......."%len(dataFromDB))
        writeRejectedPaternesToCSV(dataFromDB)

    except Exception as e:
        ColorLog.error(e)

    finally:

        if mydb:
            mydb.closeDB()
                
        driver.quit()

        # 获取输入结束
        threading._start_new_thread (beep, ((1000,2000,4000),), {'loop': 65535} )
        ColorLog.critical("exit from main ; input any key plus enter key to exit from program !!!")
        wait_any_input = input()
