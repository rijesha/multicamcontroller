#!/usr/bin/env python

import json
import os.path
import numpy as np
import cv2
import os
import logging
import mmap
from camera import camera
import serial
from threading import Thread
import time

logging.basicConfig(filename='sessions/session.log',level=logging.DEBUG)
device_port = "/dev/ttyUSB1"
has_sensor_board = False
lastdevicestring = "hello"
shutdown = False

def start_serial_device():
    global has_sensor_board
    global lastdevicestring
    ser = serial.Serial(device_port, 115200)
    firststring = ser.readline() 
    if firststring == '\n':
        ser.close()
        print("this is the arduino")
    elif firststring == '------------------------------------\r\n':
        print("this is the sensor board")
        has_sensor_board = True
        ser.reset_input_buffer()
        ser.write("stream")
        while not shutdown :
            lastdevicestring = ser.readline()
            time.sleep(.05)
    ser.close()

def nothing(x):
    pass

if __name__ == '__main__':
    cammera_list_data = open("camera_list.json").read()
    camera_list_json = json.loads(cammera_list_data)
    cameras = camera_list_json['cameras']
    cam_devices = []

    if os.path.exists(device_port):
        t = Thread(target=start_serial_device)
        t.start()

    for cam in cameras:
        if os.path.exists(cam['cam_location']):
            print("found camera: " + cam['cam_location'])
            cam_devices.append(camera(cam))


    cv2.namedWindow( 'window',cv2.WINDOW_NORMAL)
    cv2.resizeWindow('window', 2500,2000)

    max_value = [] 
    for cam in cam_devices:
        max_value.append(0)
        cv2.createTrackbar(cam.cam_num + ': Exposure','window',cam.expo,255,cam.update_exposure)
        cv2.createTrackbar(cam.cam_num + ': Gain','window',cam.gain,550,cam.update_gain)
        #cv2.createTrackbar(cam.cam_num + ': Brightness','window',cam.bright,255,cam.update_brightness)
        
    for cam in cam_devices:
        pass
        #cam.startCapturingThread()

    count = 0
    while True:
        print(lastdevicestring)
        count = count + 1
        framenum = 0
        frames = []
        output = None
        #for cam in cam_devices:
        #    cam.triggerNewFrame()

        for cam in cam_devices:
            #frame = cam.getNewFrame()
            frame = cam.read()    
            logstring = cam.generateCamLogString()
            if str(frame) != 'None' :
                blurred = cv2.blur(frame, (3, 3))
                biggest = np.amax(blurred)
                print(biggest)
                focus = cv2.Laplacian(frame, cv2.CV_32F).var()
                average = cv2.mean(frame)
                frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
                cv2.putText(frame,"max value: " + str(biggest), (100,100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"focus: " + "%.2f" % focus, (100,200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"average: " + str(average[0]), (100,300), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"exposure: " + str(cam.expo), (100,400), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"gain: " + str(cam.gain), (100,500), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                #cam.autoExpose(biggest)
                if cam.cam_num == "3":
                    print("saving cam 3")
                    cv2.imwrite("frame_" + str(count) +"_cam_" + cam.cam_num + ".png", frame)
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

    global shutdown    
    shutdown = True
