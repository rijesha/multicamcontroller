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
import mmap

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

        self.update_gain(self.gain)
        self.update_exposure(self.expo)
        self.update_brightness(self.bright)
        self.update_privacy(self.privacy)
        self.update_frame_rate()


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



def nothing(x):
    pass

if __name__ == '__main__':
    cammera_list_data = open("camera_list.json").read()
    camera_list_json = json.loads(cammera_list_data)
    cameras = camera_list_json['cameras']
    cam_devices = []

    for cam in cameras:
        if os.path.exists(cam['cam_location']):
            print("found camera: " + cam['cam_location'])
            cam_devices.append(camera(cam))
