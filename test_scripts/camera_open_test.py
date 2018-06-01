#!/usr/bin/python
import cv2
import numpy as np

cam_id = "usb-The_Imaging_Source_Europe_GmbH_DMM_42BUC03-ML_47710685-video-index0"


cap = cv2.VideoCapture("v4l2src device=/dev/v4l/by-id/" + cam_id + " ! video/x-raw,format=GRAY8,width=1280,height=960,framerate=10/1 ! videoconvert ! appsink")

#=./sessions/S_5_180524-142314/S_5_180524-142314\_frame_%04d_cam_1.jpg

while(True):
    ret, frame = cap.read()
    cv2.imshow("frame", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()