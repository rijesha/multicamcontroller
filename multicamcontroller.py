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
import threading
import serial
import wiringpi2 as wpi
import time
import logging
from camera import camera
import subprocess

import sys

logging.basicConfig(filename='sessions/session.log',level=logging.DEBUG)
device_port = "/dev/ttyUSB0"
has_sensor_board = False
lastdevicestring = "hello"
global shutdown
shutdown = False
global frame_ser
frame_ser = None
period = 1
global frame_str
frame_str = None
global session_str
frame_str = None

primaryCpuPulse = threading.Event()
primaryCpuPulse.clear()

def my_handler(type, value, tb):
    logging.exception("Uncaught exception: {0}".format(str(value)))

# Install exception handler
sys.excepthook = my_handler

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


def trigger_thread():
    global frame_str
    global session_str
    print("starting trigger Thread")
    time.sleep(1)
    frame_num = 0
    wpi.pinMode(27, 1)
    while not shutdown:
        time.sleep(period)
        frame_str = "frame_" + str(frame_num)
        frame_num = frame_num + 1
        wpi.digitalWrite(27,1)
        time.sleep(10/100000)
        wpi.digitalWrite(27,0)
        frame_ser.write(session_str + "," + frame_str + "\n")  
        primaryCpuPulse.set() 


if __name__ == '__main__':

    time.sleep(15)
    cammera_list_data = open("camera_list.json").read()
    camera_list_json = json.loads(cammera_list_data)
    cameras = camera_list_json['cameras']
    cam_devices = []
    found_cameras = 0

    isprimarycomputer = False
    for cam in cameras:
        if os.path.exists(cam['cam_location']):
            print("found camera: " + cam['cam_location'])
            logging.info("found camera: " + cam['cam_location'])
            cam_devices.append(camera(cam))
            found_cameras = found_cameras + 1
            if cam["cam_num"] == 4 :
                isprimarycomputer = True
        
    if found_cameras < 2 :
        logging.info("Did not find enough cameras. Exiting")
        exit()

    if os.path.exists(device_port):
        t = Thread(target=start_serial_device)
        t.start()
        time.sleep(5)
    
    cam_devices_up = len(cam_devices)
    for cam in cam_devices:
        cam.startCapturingThread()


    frame_ser = serial.Serial("/dev/ttyS1", 115200, timeout = None)

    wpi.wiringPiSetup()
    wpi.pinMode(0, 1)
    if isprimarycomputer:
        print("I am primary computer")
        wpi.pinMode(1, 0)
        wpi.pinMode(2, 0)
        wpi.pinMode(3, 0)
        
        logging.info("waiting for GPIO 1 to go low")
        print("waiting for GPIO 1 to go low")
        while wpi.digitalRead(1):
            time.sleep(.1)

        logging.info("waiting for GPIO 2 to go low")
        print("waiting for GPIO 2 to go low")
        while wpi.digitalRead(2):
            time.sleep(.1)


        logging.info("waiting for GPIO 3 to go low")
        print("waiting for GPIO 3 to go low")
        while wpi.digitalRead(3):
            time.sleep(.1)
        
        f = open('sessions/sessionCount.txt', 'r')
        sessionCount =  int(f.readline())
        f.close()
        f = open('sessions/sessionCount.txt', 'w')
        f.write(str(sessionCount + 1))
        f.close()
        session_str = "session_" + str(sessionCount)
        os.mkdir("sessions/" + session_str)
        logging.info("Made Directory: " + "sessions/" + session_str)
           
        if has_sensor_board:
            sensor_board_file = open("sessions/" + session_str +"/sensor_board.log", "w")
        
        t1 = Thread(target=trigger_thread)
        print "about to start thread"
        t1.start()
        
    wpi.digitalWrite(0,0)

    
    print("Ready to Start")

    devices_to_remove = []
    frame_num = 0
    flushcount = 0
    made_dirs = False


    while True:
        if isprimarycomputer :
            primaryCpuPulse.wait()
            primaryCpuPulse.clear()
                     
        else:
            try:
                frame_str = frame_ser.readline().rstrip()
                session_str, frame_str = frame_str.split(",")
            except:
                session_num = "failed"
                frame_str = "failed"
            
            frame_ser.reset_input_buffer()
        
        print frame_str
        time.sleep(0.1)
        
        if len(cam_devices) == 0:
            break
        
        #logging.info("triggering " + frame_str)
        for cam in cam_devices:
            cam.triggerNewFrame()
        
        if has_sensor_board and isprimarycomputer:
            sensor_board_file.write(frame_str + "," + lastdevicestring + '\r\n')
            flushcount = flushcount + 1
            if flushcount > 10:
                sensor_board_file.flush()
                flushcount = 0
        
        if not isprimarycomputer and not made_dirs:
            os.mkdir("sessions/" + session_str)
            logging.info("Made Directory: " + "sessions/" + session_str)
            made_dirs = True

        for cam in cam_devices:
            if cam.disconnected:
                devices_to_remove.append(cam)
            
            else :
                frame = cam.getNewFrame()

                logstring = cam.generateCamLogString()
                if str(frame) != 'None' :
                    blurred = cv2.blur(frame, (3, 3))
                    biggest = np.amax(blurred)
                    try:
                        cam.autoExpose(biggest)
                    except:
                        print("failed to change exposure")
                    
                    try:
                        cv2.imwrite("sessions/" + session_str + "/" + frame_str + "_cam_" + cam.cam_num + ".png", frame)
                        with open("sessions/" + session_str + "/" + frame_str + "_cam_" + cam.cam_num + ".txt", "w") as log_file:
                            log_file.write(logstring)
                    except:
                        made_dirs = False
                    
                    
        for d in devices_to_remove:
            d.hardclose()
            cam_devices.remove(d)
        devices_to_remove = []


    print("closing Camers")
    for cam in cam_devices:
        cam.close()

    if has_sensor_board and isprimarycomputer:
        sensor_board_file.close()
    
    shutdown = True
    subprocess.call("sync")
    print("sync finished")

    if isprimarycomputer:

        logging.info("waiting for GPIO 1 to go high")
        print("waiting for cpu 1")
        while not wpi.digitalRead(1):
            time.sleep(.1)


        logging.info("waiting for GPIO 2 to go high")
        print("waiting for cpu 2")
        while not wpi.digitalRead(2):
            time.sleep(.1)


        logging.info("waiting for GPIO 3 to go high")
        print("waiting for cpu 3")
        while not wpi.digitalRead(3):
            time.sleep(.1)
    
    wpi.digitalWrite(0,1)
    logging.info("closed: " + session_str)
