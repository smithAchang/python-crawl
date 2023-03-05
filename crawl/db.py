# -*- coding: utf-8 -*-


import os,sys,time
from datetime import datetime
from datetime import timedelta
import sqlite3
from sqlite3 import Error

if __name__ == '__main__':
    
    parentDirPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not parentDirPath in sys.path:
      sys.path.append(parentDirPath)

from crawl.colorlog import ColorLog

import unittest

'''
  MyDB
'''

class MyDB:

    def __init__(self,):
        self.con    = sqlite3.connect('mydatabase.db')
        self.cursor = self.con.cursor()
        # 可以支持升级
        self.createTables()

    def createTables(self):
        try:

            self.cursor.execute('''
                                    create table if not exists "company_query_status"(
                                      "name" TEXT NOT NULL UNIQUE,
                                      "status" TEXT NOT NULL,
                                      "date" DATE NOT NULL,
                                      PRIMARY KEY("name")
                                    )
                               ''')

            self.cursor.execute('''
                                    create table if not exists "reject_patent"(
                                      "no" TEXT NOT NULL UNIQUE,
                                      "name" TEXT NOT NULL ,
                                      "company_name" TEXT NOT NULL,
                                      "reject_date" DATE NOT NULL,
                                      PRIMARY KEY("no")
                                    )
                               ''')

            self.cursor.execute('''
                                    create table if not exists "wait_query_again_patent"(
                                      "no" TEXT NOT NULL UNIQUE,
                                      "name" TEXT NOT NULL ,
                                      "company_name" TEXT NOT NULL,
                                      "create_date" DATE NOT NULL,
                                      "update_date" DATE NOT NULL,
                                      PRIMARY KEY("no")
                                    )
                               ''')

            self.con.commit()

        except Error as e:
            ColorLog.error(e)

    def closeDB(self):
        try:
            self.cursor.close()
            self.con.commit()
            self.con.close()

            self.cursor = None
            self.con    = None

        except Error as e:
            ColorLog.error(e)

    def dropTables(self):
        try:
            self.cursor.execute("drop table if exists company_query_status")
            self.cursor.execute("drop table if exists reject_patent")
            self.cursor.execute("drop table if exists wait_query_again_patent")
            self.con.commit()

        except Error as e:
            ColorLog.error(e)

    def modCompanyQuueryStatus(self, company_name, status, date=datetime.now()):
        self.cursor.execute("select count(*) from company_query_status where name=?", (company_name,))
        rows   = self.cursor.fetchall()

        nowStr = datetime.strftime(date, "%Y-%m-%d")

        #print(rows)

        if rows[0] == (0,) :
           self.cursor.execute("insert into company_query_status values('%s','%s','%s')"%(company_name, status, nowStr))    
        else:
           self.cursor.execute("update company_query_status set status = '%s', date = '%s' where name='%s'"%(status, nowStr, company_name))    
        
        self.con.commit()

    def modRejectedPatern(self, no, name, company_name, reject_date):
        self.cursor.execute("select count(*) from reject_patent where no='%s'"%no)
        rows   = self.cursor.fetchall()

        #print(rows)

        if rows[0] == (0,) :
           self.cursor.execute("insert into reject_patent values('%s','%s','%s','%s')"%(no, name, company_name, reject_date))    
        else:
           self.cursor.execute("update reject_patent set name = '%s', company_name = '%s', reject_date = '%s' where no='%s'"%(name, company_name, reject_date, no))    
        
        self.con.commit()

    def modWaitQueryAgainPatern(self, no, name, company_name, create_date, update_date):
        self.cursor.execute("select count(*) from wait_query_again_patent where no='%s'"%no)
        rows   = self.cursor.fetchall()

        #print(rows)

        if rows[0] == (0,) :
           self.cursor.execute("insert into wait_query_again_patent values('%s','%s','%s','%s','%s')"%(no, name, company_name, create_date, update_date))    
        else:
           self.cursor.execute("update wait_query_again_patent set update_date = '%s' where no='%s'"%(update_date, no))    
        
        self.con.commit()

    def isCompanyHasBeenQueryed(self, company_name):
        self.cursor.execute("select status from company_query_status where name=?", (company_name,))
        rows = self.cursor.fetchall()

        #print(rows)

        if len(rows) == 0:
            return False

        if rows[0] != ("finished",):
            return False

        return True


    def isPaternRejected(self, no):
        self.cursor.execute("select reject_date from reject_patent where no=?", (no,))
        rows = self.cursor.fetchall()

        #print(rows)

        if len(rows) == 0:
            return False

        reject_date       = datetime.strptime(rows[0][0], "%Y-%m-%d")
        reject_date_str   = rows[0][0]

        now              = datetime.now()
        # 带有时分秒判断了格式化下仅留下日期
        threemonthago    = now - timedelta(days=90)
        threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")
        #print(reject_date, threemonthago)

        if reject_date_str < threemonthagoStr:
            return False

        return True

    def getPaternRejectedData(self, no):
        self.cursor.execute("select no, name, company_name, reject_date from reject_patent where no=?", (no,))
        rows = self.cursor.fetchall()

        #print("rows", rows)

        if len(rows) == 0:
            return None

        return rows[0]

    def getAllPaternRejectedData(self):
        self.cursor.execute("select no, name, company_name, reject_date from reject_patent order by reject_date desc,no desc")
        rows = self.cursor.fetchall()

        #print(rows)

        return rows


    def getNeedQueryAgainPaternData(self):
        now              = datetime.now()
        nowStr           = datetime.strftime(now, "%Y-%m-%d")

        someMonthago     = now - timedelta(days=45)
        someMonthagoStr  = datetime.strftime(someMonthago, "%Y-%m-%d")

        self.cursor.execute("select no, name, company_name, create_date, update_date from wait_query_again_patent where create_date <= ? and update_date != ? order by create_date", (someMonthagoStr, nowStr))
        rows = self.cursor.fetchall()

        #print('rows:', rows)

        return rows

    def getWaitQueryAgainPaternData(self, no):
      

        self.cursor.execute("select no, name, company_name, create_date, update_date from wait_query_again_patent where no= ? ", (no, ))
        rows = self.cursor.fetchall()

        if len(rows) == 0:
            return None

        return rows[0]

    def delWaitQueryAgainPaternData(self, no):
      

        self.cursor.execute("delete from wait_query_again_patent where no= ?", (no, ))
        self.con.commit()


    def deleteOldData(self):
        now    = datetime.now()
        nowStr = datetime.strftime(now, "%Y-%m-%d")
        self.cursor.execute("delete from company_query_status where date < ?", (nowStr,))

        threemonthago    = now - timedelta(days=90)
        threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")
        self.cursor.execute("delete from reject_patent where reject_date < ?", (threemonthagoStr,))
        self.cursor.execute("delete from wait_query_again_patent where create_date < ?", (threemonthagoStr,))
        self.con.commit()
             
'''
  Test Case
'''

class TestMyDB(unittest.TestCase):

    def setUp(self):
        ColorLog.info('setUp setup db ...')
        self.db = MyDB()
        self.db.dropTables()
        self.db.createTables()

    def tearDown(self):
        ColorLog.info('tearDown close db ...')
        self.db.closeDB()
        self.db = None


    def test_HasBeenQueryed(self):
        
        self.assertEqual(self.db.isCompanyHasBeenQueryed("abc"), False)

    def test_ModCompanyQueryedStatus(self):
        self.db.modCompanyQuueryStatus(u"中国", "begin")
        self.assertEqual(self.db.isCompanyHasBeenQueryed(u"中国"), False)
        self.db.modCompanyQuueryStatus(u"中国", "finished")
        self.assertEqual(self.db.isCompanyHasBeenQueryed(u"中国"), True)
        self.db.dropTables()
        self.db.createTables()
        self.assertEqual(self.db.isCompanyHasBeenQueryed(u"中国"), False)
        self.db.modCompanyQuueryStatus(u"中国", "finished")
        self.assertEqual(self.db.isCompanyHasBeenQueryed(u"中国"), True)

    def test_ModPaternRejectedStatus(self):

        now    = datetime.now()
        nowStr = datetime.strftime(now, "%Y-%m-%d")

        self.assertEqual(self.db.getPaternRejectedData('1'), None)
        self.assertEqual(self.db.isPaternRejected('1'), False)
        self.db.modRejectedPatern('1', u"中国book", u"中国", nowStr)
        self.db.modRejectedPatern('2', u"中国book2", u"中国2", nowStr)
        self.assertEqual(self.db.isPaternRejected('1'), True)

        threemonthago    = now - timedelta(days=90)
        threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")

        self.db.modRejectedPatern('1', u"中国book修改", u"中国修改", threemonthagoStr)
        self.assertEqual(self.db.getPaternRejectedData('1')[1], u"中国book修改")
        self.assertEqual(self.db.getPaternRejectedData('1')[2], u"中国修改")
        self.assertEqual(self.db.getPaternRejectedData('1')[3], threemonthagoStr)
        self.assertEqual(self.db.isPaternRejected('1'), True)

        threemonthago    = threemonthago - timedelta(days=1)
        threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")

        ColorLog.warning("maybe need be reprocessed")
        self.db.modRejectedPatern('1', u"中国book修改过期", u"中国修改过期", threemonthagoStr)
        self.assertEqual(self.db.isPaternRejected('1'), False)


    def test_deleteOldQueryData(self):
        ColorLog.info("with no data test ...")
        self.db.deleteOldData()
        company_name = u"中国"
        self.assertEqual(self.db.isCompanyHasBeenQueryed(company_name), False)
        now           = datetime.now()
        # 带有时分秒判断了格式化下仅留下日期
        onedayago     = now - timedelta(days=1)
        self.db.modCompanyQuueryStatus(company_name, "finished")
        self.assertEqual(self.db.isCompanyHasBeenQueryed(company_name), True)
        self.db.deleteOldData()
        ColorLog.info("must not be deleted")
        self.assertEqual(self.db.isCompanyHasBeenQueryed(company_name), True)

        ColorLog.info("must be deleted when expired")
        self.db.modCompanyQuueryStatus(company_name, "finished", onedayago)
        self.db.deleteOldData()
        self.assertEqual(self.db.isCompanyHasBeenQueryed(company_name), False)

    def test_deleteOldRejectData(self):
        now    = datetime.now()
        nowStr = datetime.strftime(now, "%Y-%m-%d")
        threemonthago    = now - timedelta(days=90)
        threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")

        self.db.modRejectedPatern('1', u"中国book", u"中国", nowStr)
        self.db.modRejectedPatern('2', u"中国book2", u"中国2", threemonthagoStr)
        self.assertEqual(self.db.isPaternRejected('1'), True)
        self.assertEqual(self.db.isPaternRejected('2'), True)
        self.db.deleteOldData()
        ColorLog.info("must not be deleted")
        self.assertEqual(self.db.isPaternRejected('1'), True)
        self.assertEqual(self.db.isPaternRejected('2'), True)
        
        ColorLog.info("use expired date, one item is deleted")
        threemonthago    = threemonthago - timedelta(days=1)
        threemonthagoStr = datetime.strftime(threemonthago, "%Y-%m-%d")
        self.db.modRejectedPatern('2', u"中国book2", u"中国2", threemonthagoStr)
        self.db.deleteOldData()
        self.assertEqual(self.db.isPaternRejected('1'), True)
        self.assertEqual(self.db.isPaternRejected('2'), False)

    def test_deleteWaitQueryAgainData(self):
        now              = datetime.now()
        nowStr           = datetime.strftime(now, "%Y-%m-%d")

        yestoday         = now - timedelta(days=1)
        yestodayStr      = datetime.strftime(yestoday, "%Y-%m-%d")


        someMonthago     = now - timedelta(days=46)
        someMonthagoStr  = datetime.strftime(someMonthago, "%Y-%m-%d")

        someMonthago2    = now - timedelta(days=47)
        someMonthagoStr2 = datetime.strftime(someMonthago2, "%Y-%m-%d")

        data = self.db.getWaitQueryAgainPaternData('1')
        self.assertEqual(None, data)

        self.db.modWaitQueryAgainPatern('1', u"中国book", u"中国", nowStr,nowStr)
        data = self.db.getWaitQueryAgainPaternData('1')
        self.assertEqual(('1', u"中国book", u"中国", nowStr,nowStr), data)

        datas = self.db.getNeedQueryAgainPaternData()
        self.assertEqual(datas, [])


        self.db.modWaitQueryAgainPatern('1', None, None, None, yestodayStr)
        data = self.db.getWaitQueryAgainPaternData('1')
        self.assertEqual(('1', u"中国book", u"中国", nowStr, yestodayStr), data)

        datas = self.db.getNeedQueryAgainPaternData()
        self.assertEqual(datas,[])

        self.db.modWaitQueryAgainPatern('1', None, None, None, someMonthagoStr)
        data = self.db.getWaitQueryAgainPaternData('1')
        self.assertEqual(('1', u"中国book", u"中国", nowStr, someMonthagoStr), data)

        datas = self.db.getNeedQueryAgainPaternData()
        self.assertEqual(datas, [])

        self.db.delWaitQueryAgainPaternData(('1'))

        self.db.getAllPaternRejectedData()
        self.assertEqual(datas, [])

        self.db.modWaitQueryAgainPatern('2021107878322', u"中国book1", u"中国1", someMonthagoStr, nowStr)
        self.db.modWaitQueryAgainPatern('202111411358X', u"中国book2", u"中国2", someMonthagoStr, yestodayStr)
        self.db.modWaitQueryAgainPatern('2021112116348', u"中国book3", u"中国3", someMonthagoStr2, yestodayStr)

        datas = self.db.getNeedQueryAgainPaternData()
        self.assertEqual(len(datas), 2)
        self.assertEqual(datas[0], ('2021112116348', u"中国book3", u"中国3", someMonthagoStr2, yestodayStr))
        self.assertEqual(datas[1], ('202111411358X', u"中国book2", u"中国2", someMonthagoStr, yestodayStr))
        






if __name__ == '__main__':



    ColorLog.info("test case begin to run ...")
    unittest.main()