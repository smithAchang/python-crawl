import cv2 as cv
import numpy as np
import requests
import os, sys, random,time
import shutil

if __name__ == '__main__':
    parentDirPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not parentDirPath in sys.path:
      sys.path.append(parentDirPath)


# 加载自身模块代码
from crawl.colorlog import ColorLog



def walkFiles(dirPath, oper, deep=False):
    temp = os.walk(dirPath)
    for home, childDirs, files in temp:
        if deep:  
            for childDir in childDirs:
                print('walk child dir:%s'%childDir)
                walkFiles(childDir, oper)
        
        for filename in files:
            #print('at home:%s, walk file: %s'%(home, filename))
            oper(home, filename)

# 可以调节阈值
grayThresh = 87
def grayImage(home, file):
    pathtofile = os.path.join(home, file)
    img  = cv.imread(pathtofile)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    # only white&black .white is 255, black is 0, So using INV mode will get more zero values
    ret, gray_thresh = cv.threshold(gray, grayThresh, 255, cv.THRESH_BINARY_INV)
    return gray_thresh

def splitImage(home, file):
    gray      = grayImage(home, file)
    homeSplit = os.path.join(home, 'split')
    # 需要定制
    digit1  = gray[5:31, 12:34]
    cv.imwrite(os.path.join(homeSplit, '%s.split1.png'%file), digit1)
    digit2  = gray[5:31, 35:53]
    addColums = np.zeros((digit1.shape[0], digit1.shape[1]    - digit2.shape[1]), dtype='uint8')
    digit2  = np.hstack((digit2, addColums))
    cv.imwrite(os.path.join(homeSplit, '%s.split2.png'%file), digit2)
    digit3  = gray[5:31, 54:73]
    addColums = np.zeros((digit1.shape[0], digit1.shape[1]    - digit3.shape[1]), dtype='uint8')
    digit3  = np.hstack((digit3, addColums))
    cv.imwrite(os.path.join(homeSplit, '%s.split3.png'%file), digit3)
    digit4  = gray[5:31, 74:94]
    addColums = np.zeros((digit1.shape[0], digit1.shape[1]    - digit4.shape[1]), dtype='uint8')
    digit4  = np.hstack((digit4, addColums))
    cv.imwrite(os.path.join(homeSplit, '%s.split4.png'%file), digit4)

def splitImages():
    homeSplit   = os.path.join(os.getcwd(), 'KMean', 'split')
    #clear files
    if os.path.exists(homeSplit):
        shutil.rmtree(homeSplit)
    os.makedirs(homeSplit)
    walkFiles(os.path.join(os.getcwd(), 'KMean'), splitImage)

def collectSplitImages():
    grayImages = []
    files = []
    def _collect(home, file):
        #print(file)
        files.append(file)
        grayImages.append(grayImage(home, file).T)
    walkFiles(os.path.join(os.getcwd(), 'KMean', 'split'), _collect)
    ndImages = np.array(grayImages)
    return files, ndImages

MAX_ITER = 100
# 确定邻域大小的参数
epsilon  = 0.5
def KMeanAI(ndImages, K=2):
    ndImages  = ndImages.reshape(ndImages.shape[0], -1)
    Z = np.float32(ndImages)
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, MAX_ITER, epsilon)
    compatness, labels, centers = cv.kmeans(Z, K, None, criteria, 10, cv.KMEANS_RANDOM_CENTERS)
    print('compatness: %f'%compatness)
    return labels

def svmAI(trainData, train_labels, savedFile='svm_data_kmean.dat'):
    #svmKernel = cv.ml.SVM_LINEAR
    svmKernel = cv.ml.SVM_RBF
    
    svm       = cv.ml.SVM_create()
    svm.setKernel(cv.ml.SVM_LINEAR)
    svm.setType(cv.ml.SVM_C_SVC)
    
    # all svm needs set this para
    svm.setC(2.67)

    if svmKernel == cv.ml.SVM_RBF:
        svm.setGamma(5.383)

    svm.train(trainData, cv.ml.ROW_SAMPLE, train_labels)
    svm.save(savedFile)
    result = svm.predict(trainData)[1]

    # stat
    mask = result==train_labels 
    correct = np.count_nonzero(mask)
    ColorLog.info("\r\nstat:", correct*100.0/result.size)

    svm2   = cv.ml.SVM_load(savedFile)

    result = svm2.predict(trainData)[1]

    # stat
    mask = result==train_labels 
    correct = np.count_nonzero(mask)
    ColorLog.info("\r\nstats when reload:", correct*100.0/result.size)

def downloadImages():
    downloadHome = os.path.join(os.getcwd(), 'KMean')
    for i in range(1, 10024):
        response = requests.get('https://pro.gdstc.gd.gov.cn/egrantweb/validatecode.jpg?date=%d&authCodeFunType=orgGlyInfoSearch'%time.time(), timeout=60, verify=False)
        if response.status_code != 200 :
            ColorLog.info('\r\nloop: %d in failure! status_code: %d'%(i, response.status_code))
            continue
            
        image = cv.imdecode(np.array(bytearray(response.content), dtype='uint8'), cv.IMREAD_UNCHANGED)
        cv.imwrite(os.path.join(downloadHome, '%d.png'%i), image)
        time.sleep(1)



if __name__ == '__main__':
    argc = len(sys.argv)
    if argc < 2 :
        ColorLog.notice('\r\nargc:%d\r\nUsage: program split | kmean | ai'%argc)
        sys.exit()

    arg = sys.argv[1]

    if arg == 'kmean': 
        files, ndImages = collectSplitImages()
        # 10个数字10个聚类
        labels = KMeanAI(ndImages, 10)
        ColorLog.notice('\r\ntrain data len: %d, labels: %d, these must be equal!'%(len(files), len(labels)))
        homeSplit   = os.path.join(os.getcwd(), 'KMean', 'split')
        homeCluster = os.path.join(os.getcwd(), 'KMean', 'cluster')

        #clear files
        if os.path.exists(homeCluster):
            shutil.rmtree(homeCluster)
        
        os.makedirs(homeCluster)

        for i in range(len(labels)):
            fileSrc = files[i]
            fileDst = '%02d_%s'%(labels[i], files[i])
            shutil.copyfile(os.path.join(homeSplit, fileSrc), os.path.join(homeCluster, fileDst))
            i += 1
    elif arg == 'split' :
        pass
    elif arg == 'ai' :
        pass    
