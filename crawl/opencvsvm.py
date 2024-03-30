#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
  
'''

import os,sys,base64,math
import numpy as np
import cv2 as cv
import time

if __name__ == '__main__': 
    homePath = os.getcwd()
    if homePath not in sys.path:
        sys.path.append(homePath)

from crawl.colorlog import ColorLog

def svmAI(trainData, train_labels, kernel=cv.ml.SVM_LINEAR, savedFile='svm_vector_data.dat'):
    svm = cv.ml.SVM_create()
    svm.setKernel(kernel)
    svm.setType(cv.ml.SVM_C_SVC)
    svm.setC(2.67)

    if kernel != cv.ml.SVM_LINEAR:
        svm.setGamma(5.383)

    svm.train(trainData, cv.ml.ROW_SAMPLE, train_labels)
    svm.save(savedFile)
    result = svm.predict(trainData)[1]

    # stat
    mask = result==train_labels 
    correct = np.count_nonzero(mask)
    ColorLog.info("stat: %f"%(correct*100.0/result.size))

    svmReload   = cv.ml.SVM_load(savedFile)

    result = svmReload.predict(trainData)[1]

    # stat
    mask = result==train_labels 
    correct = np.count_nonzero(mask)
    ColorLog.info("stats after reload: %f"%(correct*100.0/result.size))
    return svmReload

def produceNonSeenSamples(maxSamples, non_zerofields):
    samples = []
    
    ColorLog.info("will produce %d sample  ..."%maxSamples)
    
    
    while True:
        sampleSum  = len(samples)        
        sample = np.random.randint(low=0, high=2, size=10, dtype='int')
    
        if sampleSum < maxSamples and np.count_nonzero(sample) == non_zerofields :
            samples.append(sample)
            
        if sampleSum >= maxSamples :
            ColorLog.info("has reach the sum(%d) for %d non-zero fields of big data sample..."%(maxSamples, non_zerofields))
            break
       
    trainData    = np.array(samples)
    trainData    = np.float32(trainData)
    return trainData
    

if __name__ == '__main__':
    
    positiveSamples = []
    negativeSamples = []
    
    ColorLog.info("the vector space is 200 less or more ...")
    
    BIGDATASUM = 2000
    
    while True:
        positiveSampleSum  = len(positiveSamples)
        negativeSampleSum = len(negativeSamples)
        
        sample = np.random.randint(low=0, high=2, size=10, dtype='int')
    
        if positiveSampleSum < BIGDATASUM and np.count_nonzero(sample) == 4 :
            positiveSamples.append(sample)
        elif negativeSampleSum < BIGDATASUM and np.count_nonzero(sample) == 5:
            negativeSamples.append(sample)
            
        if positiveSampleSum >= BIGDATASUM and negativeSampleSum >= BIGDATASUM:
            ColorLog.info("has reach the sum(%d) of big data sample..."%BIGDATASUM)
            break
       
    nd_positiveSamples   = np.array(positiveSamples)
    nd_negativeSamples   = np.array(negativeSamples)
    datasetFile='nonzero_field_archive.npz'
    ColorLog.info("save data set in %s"%datasetFile)    
    np.savez(datasetFile, array1=nd_positiveSamples, array2=nd_negativeSamples)
    trainData    = np.concatenate((nd_positiveSamples, nd_negativeSamples))
    trainData    = np.float32(trainData)
    
    positive_labels = np.repeat(1, BIGDATASUM)[:, np.newaxis]
    negative_labels = np.repeat(0, BIGDATASUM)[:, np.newaxis]
    train_labels    = np.concatenate((positive_labels, negative_labels))
    ColorLog.info("trainData.shape: %s, train_labels.shape: %s ..."%(trainData.shape, train_labels.shape))
            
    svmReload = svmAI(trainData, train_labels)
     
    for nonzerosum in range(1, 11):
        testData = produceNonSeenSamples(BIGDATASUM, nonzerosum)
        result   = svmReload.predict(testData)[1]

        # stat
        mask = result==negative_labels 
        correct = np.count_nonzero(mask)
        ColorLog.info("test with %d non-zero fields, has negative stat: %f\n"%(nonzerosum, correct*100.0/result.size))    
      
    

