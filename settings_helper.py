#!/usr/bin/env python

import json
import os.path
import numpy as np
import cv2
import os
import logging
import mmap
from camera import camera

def nothing(x):
    pass

if __name__ == '__main__':
    cammera_list_data = open("camera_list.json").read()
    camera_list_json = json.loads(cammera_list_data)
    cameras = camera_list_json['cameras']
    cam_devices = []
    #for cam in cameras:
    #    if os.path.exists(cam['cam_location']):
    #        print("found camera: " + cam['cam_location'])
    #        cam_dev = camera(cam)
    #        cam_dev.setuphack()


    for cam in cameras:
        if os.path.exists(cam['cam_location']):
            print("found camera: " + cam['cam_location'])
            cam_devices.append(camera(cam))


    cv2.namedWindow( 'window',cv2.WINDOW_NORMAL)
    cv2.resizeWindow('window', 1500,1000)

    max_value = [] 
    for cam in cam_devices:
        max_value.append(0)
        cv2.createTrackbar(cam.cam_num + ': Exposure','window',cam.expo,255,cam.update_exposure)
        cv2.createTrackbar(cam.cam_num + ': Gain','window',cam.gain,550,cam.update_gain)
        cv2.createTrackbar(cam.cam_num + ': Brightness','window',cam.bright,255,cam.update_brightness)
        
    for cam in cam_devices:
        cam.startCapturingThread()

    count = 0
    while True:
        count = count + 1
        framenum = 0
        frames = []
        output = None
        for cam in cam_devices:
            cam.triggerNewFrame()

        for cam in cam_devices:
            frame = cam.getNewFrame()    
            logstring = cam.generateCamLogString()
            if str(frame) != 'None' :
                biggest = np.amax(frame)
                focus = cv2.Laplacian(frame, cv2.CV_32F).var()
                average = cv2.mean(frame)
                frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
                cv2.putText(frame,"max value: " + str(biggest), (100,100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"focus: " + "%.2f" % focus, (100,200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"average: " + str(average[0]), (100,300), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"exposure: " + str(cam.expo), (100,400), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"gain: " + str(cam.gain), (100,500), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cam.autoExpose(average[0])
                frames.append(frame)
                if str(output) == 'None':
                    output = frame
                else:
                    output = np.hstack((output, frame))
            framenum = framenum + 1

        # Display the resulting frame
        cv2.imshow( "window",output)
        if cv2.waitKey(1000) & 0xFF == ord('q'):
            break

    print("closing Camers")
    for cam in cam_devices:
        cam.close()
