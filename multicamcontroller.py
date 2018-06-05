#!/usr/bin/env python

import json
import os.path
import numpy as np
import cv2
import os
import v4l2capture
import select
import time
import v4l2
import fcntl
from threading import Thread
import serial
import wiringpi2 as wpi
import time
import argparse
import logging
from camera import camera

logging.basicConfig(filename='sessions/session.log',level=logging.DEBUG)
device_port = "/dev/ttyUSB0"
has_sensor_board = False
lastdevicestring = "hello"
shutdown = False

def start_serial_device():
    global has_sensor_board
    global lastdevicestring
    print("starting Serial Device")
    ser = serial.Serial(device_port, 115200)
    ser.readline()
    ser.readline()
    firststring = ser.readline()
    print("the first line is: " + firststring)


    if 'USB Camera HUB Board' in firststring:
        ser.close()
        print("this is the arduino")
    elif "Timing" in firststring:
        print("this is the sensor board")
        has_sensor_board = True
        ser.reset_input_buffer()
        ser.write("stream")
        while not shutdown :
            lastdevicestring = ser.readline()
            time.sleep(.07)
    ser.close()
    

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='USB cam hub')
    parser.add_argument('-p','--pausetime', default=45, type=int, help='time to pause.', nargs='?')
    args = parser.parse_args()

    time.sleep(10)
    cammera_list_data = open("camera_list.json").read()
    camera_list_json = json.loads(cammera_list_data)
    cameras = camera_list_json['cameras']
    cam_devices = []
    found_cameras = False
    for cam in cameras:
        if os.path.exists(cam['cam_location']):
            print("found camera: " + cam['cam_location'])
            logging.info("found camera: " + cam['cam_location'])
            cam_devices.append(camera(cam))
            found_cameras = True
        
    if not found_cameras :
        exit()

    if os.path.exists(device_port):
        t = Thread(target=start_serial_device)
        t.start()
        time.sleep(5)

    wpi.wiringPiSetup()
    wpi.pinMode(0, 0)

    frame_num = 0
    usecs = 10
    timesincelast = time.time()
    currenttime = 0   

    f = open('sessions/sessionCount.txt', 'r')
    sessionCount =  int(f.readline())
    f.close()
    f = open('sessions/sessionCount.txt', 'w')
    f.write(str(sessionCount + 1))
    f.close()
    sessionCount = str(sessionCount)
    os.mkdir("sessions/session_" + sessionCount)

    logging.info("Made Directory: " + "sessions/session_" + sessionCount)

    if has_sensor_board:
        sensor_board_file = open("sessions/session_" + sessionCount +"/sensor_board.log", "w")
    
    for cam in cam_devices:
        cam.startCapturingThread()

    while True:
        if wpi.digitalRead(0):
            currenttime = time.time()
            timesincelast = currenttime 
            time.sleep(.07)
            frame_num = frame_num + 1
            logging.info("reading frame: " + str(frame_num))

            for cam in cam_devices:
                cam.triggerNewFrame()
            if has_sensor_board:
                sensor_board_file.write("frame= %s," % str(frame_num) + lastdevicestring)
                sensor_board_file.flush()

            for cam in cam_devices:
                frame = cam.getNewFrame()
                logstring = cam.generateCamLogString()
                if str(frame) != 'None' :
                    average = cv2.mean(frame)
                    cam.autoExpose(average[0])
                    cv2.imwrite("sessions/session_" + sessionCount + "/frame_" + str(frame_num) + "_cam_" + cam.cam_num + ".png", frame)
                    with open("sessions/session_" + sessionCount + "/frame_" + str(frame_num) + "_cam_" + cam.cam_num + ".txt", "w") as log_file:
                        log_file.write(logstring)
        else:
            time.sleep(usecs/1000000.0)

    print("closing Camers")
    for cam in cam_devices:
        cam.close()

    if has_sensor_board:
        sensor_board_file.close()
