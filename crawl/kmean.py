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

homeAI          = os.path.join(os.getcwd(),  "ai")
ai_data_file    = os.path.join(homeAI,       'svm_data_kmean.dat')
homeKMean       = os.path.join(os.getcwd(),  "KMean")

homeDownload    = os.path.join(homeKMean,    "download")
homeSplit       = os.path.join(homeKMean,    "split")
homeCluster     = os.path.join(homeKMean,   'cluster')
# for train AI
homeDigits      = os.path.join(homeKMean,   'digits')


def walkFiles(dirPath, oper, deep=False):
    # os.walk is a generator
    for home, childDirs, files in os.walk(dirPath):
        if deep:  
            for childDir in childDirs:
                print('walk child dir:%s'%childDir)
                walkFiles(childDir, oper)
        
        for filename in files:
            #print('at home:%s, walk file: %s'%(home, filename))
            oper(home, filename)


def grayImageFile(home, file):
    pathtofile = os.path.join(home, file)
    img  = cv.imread(pathtofile)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    return gray

# 可以调节阈值
grayThresh = 87
def grayAndThreshImage(home, file):
    gray = grayImageFile(home, file)
    # only white&black .white is 255, black is 0, So using INV mode will get more zero values
    ret, gray_thresh = cv.threshold(gray, grayThresh, 255, cv.THRESH_BINARY_INV)
    return gray_thresh


def splitWebImageForAi(img):
    gray             = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    ret, gray_thresh = cv.threshold(gray, grayThresh, 255, cv.THRESH_BINARY_INV)
    return splitImage(gray_thresh)

def splitImage(img):
    # 需要定制
    digit1  = img[5:31, 12:34]
    
    digit2  = img[5:31, 35:53]
    addColums = np.zeros((digit1.shape[0], digit1.shape[1]    - digit2.shape[1]), dtype='uint8')
    digit2  = np.hstack((digit2, addColums))
    
    digit3  = img[5:31, 54:73]
    addColums = np.zeros((digit1.shape[0], digit1.shape[1]    - digit3.shape[1]), dtype='uint8')
    digit3  = np.hstack((digit3, addColums))
    
    digit4  = img[5:31, 74:94]
    addColums = np.zeros((digit1.shape[0], digit1.shape[1]    - digit4.shape[1]), dtype='uint8')
    digit4  = np.hstack((digit4, addColums))
    return digit1, digit2, digit3, digit4


def splitImageFile(home, file):
    gray      = grayAndThreshImage(home, file)
    return splitImage(gray)

def splitImageToFile(home, file):
    digit1, digit2, digit3, digit4      = splitImageFile(home, file)
    
    # 需要定制
    cv.imwrite(os.path.join(homeSplit, '%s.split1.png'%file), digit1)
    cv.imwrite(os.path.join(homeSplit, '%s.split2.png'%file), digit2)
    cv.imwrite(os.path.join(homeSplit, '%s.split3.png'%file), digit3)
    cv.imwrite(os.path.join(homeSplit, '%s.split4.png'%file), digit4)

def splitImages():
    #clear files
    if os.path.exists(homeSplit):
        shutil.rmtree(homeSplit)
    os.makedirs(homeSplit)

    walkFiles(homeDownload, splitImageToFile)

def collectSplitImages():
    grayImages = []
    files      = []
    def _collect(home, file):
        #print(file)
        files.append(file)
        grayImages.append(grayAndThreshImage(home, file).T)

    walkFiles(homeSplit, _collect)
    ndImages = np.array(grayImages)
    return files, ndImages

MAX_ITER = 1000
# 确定邻域大小的参数
epsilon  = 0.5
def KMeanAI(ndImages, K=2):
    ndImages  = ndImages.reshape(ndImages.shape[0], -1)
    Z         = np.float32(ndImages)
    criteria  = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, MAX_ITER, epsilon)
    compatness, labels, centers = cv.kmeans(Z, K, None, criteria, 10, cv.KMEANS_RANDOM_CENTERS)
    ColorLog.info('compatness: %f'%compatness)
    return labels

def collectDigitTrainData(home, file, train_samples):
    # without thresh process because it has been threshed
    trainDigitImg  = grayImageFile(home, file)
    # 利用转置
    train_samples.append(trainDigitImg.T)


def produceTrainData():
    samples   = []
    ndLabels  = np.array([], dtype='uint8')
    for i in range(10):
        eachDigitHome = os.path.join(homeDigits, str(i))
        oldLen        = len(samples)
        walkFiles(eachDigitHome, lambda home, file: collectDigitTrainData(home, file, samples))
        ndLabels      = np.hstack((ndLabels, np.repeat(i, len(samples) - oldLen)))
    
    ColorLog.info("before reshape Samples:%d, ndLabels:%s"%(len(samples), str(ndLabels.shape)))
    ndLabels  = ndLabels.reshape(ndLabels.shape[0], -1)
    ndSamples = np.array(samples)
    ndSamples = np.float32(ndSamples).reshape(ndSamples.shape[0], -1)
    ColorLog.info("ndSamples:%s, ndLabels:%s"%(str(ndSamples.shape), str(ndLabels.shape)))
    return ndSamples, ndLabels

svmKernel = cv.ml.SVM_LINEAR
#svmKernel = cv.ml.SVM_RBF
def svmAI(trainData, train_labels, savedFile=ai_data_file):
    
    
    svm       = cv.ml.SVM_create()
    svm.setKernel(svmKernel)
    svm.setType(cv.ml.SVM_C_SVC)
        
    # all svm needs set this para
    svm.setC(2.67)
    
    if svmKernel == cv.ml.SVM_RBF:
        svm.setGamma(5.383)
    
    ColorLog.info("svmKernel: %d, trainData shape:%s, train_labels shape:%s"%(svmKernel, str(trainData.shape), str(train_labels.shape)))
    #ColorLog.info("trainData:%s"%(str(trainData[0])))
    #ColorLog.info("train_labels:%s"%(str(train_labels)))
    svm.train(trainData, cv.ml.ROW_SAMPLE, train_labels)
    svm.save(savedFile)
    result = svm.predict(trainData)[1]
    
    # stat
    mask = result==train_labels 
    correct = np.count_nonzero(mask)
    ColorLog.info("stat: %f"%((correct*100.0)/result.size))
    
    svm2   = cv.ml.SVM_load(savedFile)
    
    result = svm2.predict(trainData)[1]
    
    # stat
    mask = result == train_labels 
    correct = np.count_nonzero(mask)
    ColorLog.info("stats when reload:%f"%((correct*100.0)/result.size))

def downloadImages():
    
    for i in range(1, 10024):
        response = requests.get('https://pro.gdstc.gd.gov.cn/egrantweb/validatecode.jpg?date=%d&authCodeFunType=orgGlyInfoSearch'%time.time(), timeout=60, verify=False)
        if response.status_code != 200 :
            ColorLog.info('loop: %d in failure! status_code: %d'%(i, response.status_code))
            continue
            
        image = cv.imdecode(np.array(bytearray(response.content), dtype='uint8'), cv.IMREAD_UNCHANGED)
        cv.imwrite(os.path.join(homeDownload, '%d.png'%i), image)
        time.sleep(1)


def predictDigit(svm, digitImg):
    #ColorLog.notice('input shape:%s'%str(digitImg.shape))
    digitImg      = np.array(digitImg.T)
    digitImg      = np.float32(digitImg)
    #ColorLog.notice('after transform shape:%s'%str(digitImg.shape))
    
    digitImg = digitImg.reshape(1, -1)
    #ColorLog.notice('after reshape:%s'%str(digitImg.shape))
    result   = svm.predict(digitImg)[1]
    result   = np.int16(result)
    return result[0][0]


def bootstrapSplit(home, file, svm, homeSplit):
    j = 1
    for digitImg in splitImageFile(home, file):
        digit    = predictDigit(svm, digitImg)
        cv.imwrite(os.path.join(homeSplit, '%d'%digit, '%s.split%d.png'%(file, j)), digitImg)
        j += 1

def getSvm():
     svm       = cv.ml.SVM_load(ai_data_file)
     return svm

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc < 2 :
        ColorLog.notice('argc:%d\r\nUsage: program split | kmean | ai'%argc)
        sys.exit()
    
    arg = sys.argv[1]
    
    ColorLog.notice('input args: %s'%sys.argv[1:])
    
    if arg == 'kmean': 
        files, ndImages = collectSplitImages()
        # 10个数字10个聚类
        labels = KMeanAI(ndImages, 10)
        ColorLog.notice('train data len: %d, labels: %d, these must be equal!'%(len(files), len(labels)))
        
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
        splitImages()
    elif arg == 'bootstrapSplit' :
        svm         = cv.ml.SVM_load(ai_data_file)
        if argc > 2:
            homeSplit   = os.path.join(homeKMean, sys.argv[2])
        else:
            homeSplit   = os.path.join(homeKMean, 'bootstrapSplit')

        #clear files
        if os.path.exists(homeSplit):
            shutil.rmtree(homeSplit)
        os.makedirs(homeSplit)
        for i in range(10):
            os.makedirs(os.path.join(homeSplit, '%d'%i))

        walkFiles(homeDownload, lambda home, file: bootstrapSplit(home, file, svm, homeSplit))

    elif arg == 'ai' :
        if argc > 2:
            homeDigits   = os.path.join(homeKMean, sys.argv[2])
       
        if argc > 3:
            ai_data_file = sys.argv[3]

        ndSamples, ndLabels = produceTrainData()
        ColorLog.info('at %s dir, ndSamples:%s, ndLabels:%s'%(homeDigits, str(ndSamples.dtype), str(ndLabels.dtype)))
        svmAI(ndSamples, ndLabels, ai_data_file)
    elif arg == 'useAi' :
        svm       = cv.ml.SVM_load(ai_data_file)
        homeTest  = os.path.join(homeKMean, "test")
        testFile  = sys.argv[2]
        j = 1
        for digitImg in splitImageFile(homeTest, testFile):
            cv.imwrite(os.path.join(homeTest, '%s.split%d_add.png'%(testFile, j)), digitImg)
            digit   = predictDigit(svm, digitImg)
            ColorLog.notice('test file : %s, data shape: %s; predict labels: %d ...'%(testFile, str(digitImg.shape), digit))
            j += 1
    elif arg == 'useAi2' :
        svm       = cv.ml.SVM_load(ai_data_file)
        homeTest  = os.path.join(homeKMean, "test")
        testFile  = sys.argv[2]
        
        checkCodeImg        = cv.imread(os.path.join(homeTest, testFile))
        checkCodeImg_zoom   = cv.resize(checkCodeImg, (97, 37), interpolation = cv.INTER_CUBIC)

        j = 1
        for digitImg in splitWebImageForAi(checkCodeImg_zoom):
            cv.imwrite(os.path.join(homeTest, '%s.split%d_add.png'%(testFile, j)), digitImg)
            digit   = predictDigit(svm, digitImg)
            ColorLog.notice('test file : %s, data shape: %s; predict labels: %d ...'%(testFile, str(digitImg.shape), digit))
            j += 1
