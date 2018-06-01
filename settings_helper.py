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
        self.video.create_buffers(1)
        self.video.queue_all_buffers()

        self.update_gain(self.gain)
        self.update_exposure(self.expo)
        self.update_brightness(self.bright)
        self.update_privacy(self.privacy)
        self.update_frame_rate()

        self.video.start()
        #try:
        #    self.video.read_and_queue()
        #except:
        #    print("COuldnt read queue")

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
        image_data = self.video.read_and_queue()

    def setuphack(self):
        timeout = 1
        readable, writable, exceptional = select.select((self.video.fileno(),), (), (), timeout)

        print("inside setupHack timeout")
        print(readable)
        if not readable:
            print 'timed out, do some other work here'
        
        self.close()


    def read(self):
        select.select((self.video.fileno(),), (), ())
        image_data = self.video.read_and_queue()

        if len(image_data) != 1228800:
            print("FAILED")
            return None
        return np.fromstring(image_data, np.uint8).reshape(960,1280)

    def close(self):
        self.video.stop()
        self.video.close()


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
        cv2.createTrackbar(cam.cam_num + ': Gain','window',cam.gain,255,cam.update_gain)
        cv2.createTrackbar(cam.cam_num + ': Brightness','window',cam.bright,255,cam.update_brightness)
        

    count = 0
    while True:
        count = count + 1
        framenum = 0
        frames = []
        output = None
        for cam in cam_devices:
            frame = cam.read()
            if str(frame) != 'None' :
                biggest = np.amax(frame)
                focus = cv2.Laplacian(frame, cv2.CV_32F).var()
                frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
                cv2.putText(frame,"max value: " + str(biggest), (100,100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
                cv2.putText(frame,"focus: " + "%.2f" % focus, (100,200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0),3)
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
