#!/usr/bin/python3

'''
  根据Excel中数据，爬虫目标网站，获取姓名、电话和电子邮箱
'''

import logging
import time,datetime

import requests
from lxml import etree
import xlwt
import csv
import xlrd
from xlutils.copy import copy

# 实例化对象
begin = datetime.datetime.today()
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logging.info("begin to test ...")


class CanNotMeetCrawlConditions(Exception):
	pass

def processResponse(response):
   result = []

   if response.status_code != 200:
   	 logging.error("crawl in failure " + str(response.status_code))
   	 return result
   
   root        = etree.HTML(response.content)
   contentdiv  = root.xpath("//body/div[@class='new_cont']")
   contenttext = contentdiv[0].xpath('string(.)')
   contentlist = contenttext.replace(' ','').replace('\r\n\r\n\r\n','\r\n').split('\r\n')

   itemindex   = -1
   for item in contentlist:
   	 itemindex +=1
   	 if item.startswith("姓名"):
   	 	logging.info('find anchor item：' + item)
   	 	break
   	 else:
   	    logging.debug('common analysed item：' + item)
   else:
   	 logging.critical("the response format is changed, can not meet the crawl conditions !")
   	 raise CanNotMeetCrawlConditions("the response format is changed, can not meet the crawl conditions !" + str(params))

  
   if itemindex != -1:
   	result.append(contentlist[itemindex + 1 ])
   	result.append(contentlist[itemindex + 3 ])
   	result.append(contentlist[itemindex + 5 ])

   return result


def crawlPageGet(url, params):
  
   response    = requests.get('https://pro.gdstc.gd.gov.cn/egrantweb/reg-organization/toOrgSameName', params=params, timeout=10, verify=False)

   return processResponse(response)

def crawlPagePost(url, formdata):

	headers     = {'Content-Type':'application/x-www-form-urlencoded'}
	#data        = {'orgNoType':1,'orgNo':'MA59HCME4'}
	response    = requests.post('https://pro.gdstc.gd.gov.cn/egrantweb/reg-organization/toOrgSameName', headers=headers, data=formdata, timeout=10, verify=False)
	return processResponse(response)

def writeQueryResult(new_worksheet, result):
   write_name_cell_pos = 2
   new_worksheet.write(row, write_name_cell_pos,      result[0])
   new_worksheet.write(row, write_name_cell_pos + 1 , result[1])
   new_worksheet.write(row, write_name_cell_pos + 2,  result[2])

if __name__ == '__main__':

   # 放在当前目录,可以只输入文件名
   pathtofile   = u"data.xls"


   try:
      workbook  = xlrd.open_workbook(pathtofile)  # 打开工作簿
      sheets    = workbook.sheet_names()  # 获取工作簿中的所有表格
      worksheet = workbook.sheet_by_name(sheets[0])  # 获取工作簿中所有表格中的的第一个表格
      rows      = worksheet.nrows  # 获取表格中已存在的数据的行数

      logging.info("create new sheet for write form old file ...")
      new_workbook  = copy(workbook)  # 将xlrd对象拷贝转化为xlwt对象
      new_worksheet = new_workbook.get_sheet(0)  # 获取转化后工作簿中的第一个表格
      new_workbook.save(pathtofile)  # 尝试保存，以避免最后出现保存错误

      logging.debug("first row is logo and second row is headers ...")

      for row in range(2, rows):
      	orgName  = worksheet.cell_value(row, 0)
      	creditNo = worksheet.cell_value(row, 1)
      	logging.debug("cellvalue: " + orgName + " ,creditNo: " + creditNo + " ,creditNoLen: " + str(len(creditNo)))

      	result   = crawlPageGet('https://pro.gdstc.gd.gov.cn/egrantweb/reg-organization/toOrgSameName', {'checkType': 2, 'orgName': orgName})

      	if len(result) != 0 :
      	 
      	  if len(result[0]) == 0:
      	   orgNo           = creditNo[-10 : -1 : 1] # 特殊场景
      	   logging.warning("cellvalue:" + orgName + " is needed query orgNo("+ orgNo + ") by post method at row: " + str(row))
      	   formdata        =  {'orgNoType': 1, 'orgNo': orgNo}
      	   result          = crawlPagePost('https://pro.gdstc.gd.gov.cn/egrantweb/reg-organization/toOrgSameName', formdata)

      	   if len(result) == 0 :
      	   	 logging.error("try to query by orgNo failed !\r\n\r\n")
      	   	 continue

      	else:
      	   logging.error("query failed  with no result, please check!\r\n\r\n")
      	   continue
     
      	logging.info("\r\n\r\n公司名称: " + orgName + " , 统一社会信用代码: " + creditNo +  "\r\n姓名:     " + result[0] + " , 姓名长度: " + str(len(result[0])) + "\r\n联系电话: " + result[1] + "\r\n电子邮件: " + result[2] + "\r\n")
      	writeQueryResult(new_worksheet, result)

      new_workbook.save(pathtofile)  # 保存工作簿
      logging.info("save query results, crawl successfully !!")

   finally:
      end = datetime.datetime.today()
      logging.warning("exit from process, totally use {} seconds !!!".format((end - begin).seconds))
      time.sleep(5)