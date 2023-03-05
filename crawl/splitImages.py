import cv2 as cv
import numpy as np


def LoadTemplateImages():
    digits = []

    for i in range(0, 10):
     img = cv.imread('./template/%d.png'%i)
     digits.append(img)

    plusOper = cv.imread('./template/plusOper.png')

    return (digits, plusOper)    

def specialProcessArithmeticCheckcodeImage(checkcodeImage):
     checkcodeImage   = checkcodeImage.copy()
     img_gray         = cv.cvtColor(checkcodeImage, cv.COLOR_BGR2GRAY)
     ret, thresh      = cv.threshold(img_gray, 127, 255, cv.THRESH_BINARY)
     normalChannelImg = cv.cvtColor(thresh, cv.COLOR_GRAY2BGR) 
     return normalChannelImg

def splitArithmeticCheckcodeImage(checkcodeImage):
     img_proceessed    = SpecialProcessArithmeticCheckcodeImage(checkcodeImage)
     
     lhs               = img_proceessed[:, :12]
     oper              = img_proceessed[:, 13:25]
     rhs               = img_proceessed[:, 27:39]

     return (lhs, oper, rhs)

def zoomOriImage(img):
    candyPara = (100, 200)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    ret, gray_thresh = cv.threshold(gray, 127, 255, cv.THRESH_BINARY)
    blur = cv.blur(gray_thresh ,(3, 3))
    ret, blur_thresh = cv.threshold(blur, 127, 255, cv.THRESH_BINARY)
    zoom = cv.resize(blur_thresh, None, fx=7, fy=7, interpolation = cv.INTER_CUBIC)
    edges = cv.Canny(zoom, *candyPara)
    return edges






if __name__ == '__main__':
  for i in range(1, 100):
    res = splitArithmeticCheckcodeImage(cv.imread('./authImg/%dimage.png'%i))
    cv.imwrite('./split/lhs%dimage.png'%i,  res[0])
    cv.imwrite('./split/oper%dimage.png'%i, res[1])
    cv.imwrite('./split/rhs%dimage.png'%i,  res[2])

