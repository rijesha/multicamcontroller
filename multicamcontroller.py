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

device_port = "/dev/ttyUSB0"

class camera:
    def __init__(self, cam_data):
        self.cam_data = cam_data
        self.video = v4l2capture.Video_device(cam_data['cam_location'])
        self.cam_num = str(cam_data["cam_num"])
        self.expo = cam_data["exposure_absolute"]
        self.bright = cam_data["brightness"]
        self.gain = cam_data["gain"]
        self.privacy = cam_data["privacy"]
        size_x, size_y = self.video.set_format(1280, 960, 1)
        self.video.create_buffers(1)
        self.video.queue_all_buffers()

        self.update_gain(self.gain)
        self.update_exposure(self.expo)
        self.update_brightness(self.bright)
        self.update_privacy(self.privacy)
        self.update_frame_rate()

        self.video.start()

    def update_gain(self, value):
        c = v4l2.v4l2_control()
        c.id = v4l2.V4L2_CID_GAIN
        c.value = value
        fcntl.ioctl(self.video, v4l2.VIDIOC_S_CTRL, c)

    def update_exposure(self, value):
        c = v4l2.v4l2_control()
        c.id = v4l2.V4L2_CID_EXPOSURE_ABSOLUTE
        c.value = value
        fcntl.ioctl(self.video, v4l2.VIDIOC_S_CTRL, c)

    def update_brightness(self, value):
        c = v4l2.v4l2_control()
        c.id = v4l2.V4L2_CID_BRIGHTNESS
        c.value = value
        fcntl.ioctl(self.video, v4l2.VIDIOC_S_CTRL, c)

    def update_privacy(self, value):
        c = v4l2.v4l2_control()
        c.id = v4l2.V4L2_CID_PRIVACY
        #c.value = cam_data["privacy"]
        c.value = value
        fcntl.ioctl(self.video, v4l2.VIDIOC_S_CTRL, c)

    def update_frame_rate(self):
        c = v4l2.v4l2_streamparm()
        c.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        c.parm.capture.timeperframe.numerator = 1
        c.parm.capture.timeperframe.denominator = 10
        fcntl.ioctl(self.video.fileno(), v4l2.VIDIOC_S_PARM, c)

    def clearBuffer(self):
        select.select((self.video,), (), ())
        image_data = self.video.read()

    def read(self, retry = 1):
        print("reading one")
        select.select((self.video.fileno(),), (), ())
        image_data = self.video.read_and_queue()

        if len(image_data) != 1228800:
            print("FAILED " + self.cam._num + " -- retrying")
            if retry > 0 :
                return self.read(retry - 1)
            else :
                return None
        return np.fromstring(image_data, np.uint8).reshape(960,1280)

    def close(self):
        self.video.stop()
        self.video.close()


def delay_trigger(seconds):
    ser = serial.Serial(device_port, 115200)
    time.sleep(5)
    ser.write("AT+STOP")
    time.sleep(seconds)
    ser.write("AT+START")
    ser.close()
    print("closed Serial")
    

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='USB cam hub')
    parser.add_argument('-p','--pausetime', default=45, type=int, help='time to pause.', nargs='?')
    args = parser.parse_args()
    
    
    #Check if usb serial port exists. If so then we have control of the trigger.
    if os.path.exists("/dev/ttyUSB0"):
        t = Thread(target=delay_trigger, args=(args.pausetime,))
        t.start()

    time.sleep(10)
    cammera_list_data = open("camera_list.json").read()
    camera_list_json = json.loads(cammera_list_data)
    cameras = camera_list_json['cameras']
    cam_devices = []
    found_cameras = False
    for cam in cameras:
        if os.path.exists(cam['cam_location']):
            print("found camera: " + cam['cam_location'])
            cam_devices.append(camera(cam))
            found_cameras = True
        
    if not found_cameras :
        exit()

    wpi.wiringPiSetup()
    wpi.pinMode(0, 0)

    frame_num = 0
    usecs = 10
    timesincelast = time.time()
    currenttime = 0

    #make sure no trigger is sent for at least 3 seconds
    trig_count = 3
    loop_count = 0
    triggered = False
    print("starting 3 second no pulse wait")
    while trig_count is not 0:
        loop_count = loop_count + 1
        if wpi.digitalRead(0):
            trig_count = 3
            print("got new trigger")
        time.sleep(usecs/1000000.0)
        if loop_count == 10000 :
            print("subtracting count")
            trig_count = trig_count - 1
            loop_count = 0
        

    f = open('sessions/sessionCount.txt', 'r')
    sessionCount =  int(f.readline())
    f.close()
    f = open('sessions/sessionCount.txt', 'w')
    f.write(str(sessionCount + 1))
    f.close()
    sessionCount = str(sessionCount)
    os.mkdir("sessions/session_" + sessionCount)

    while True:
        if wpi.digitalRead(0):
            currenttime = time.time()
            timesincelast = currenttime 
            time.sleep(.05)
            frame_num = frame_num + 1
            for cam in cam_devices:
                frame = cam.read()
                if str(frame) != 'None' :
                    cv2.imwrite("sessions/session_" + sessionCount + "/frame_" + str(frame_num) + "_cam_" + cam.cam_num + ".png", frame)
        else:
            time.sleep(usecs/1000000.0)

    print("closing Camers")
    for cam in cam_devices:
        cam.close()
