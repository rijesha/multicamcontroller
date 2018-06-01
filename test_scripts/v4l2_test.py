#!/usr/bin/env python

import numpy as np
import cv2
import os
import v4l2capture
import select
import time
import v4l2
import fcntl

if __name__ == '__main__':
    #cap = cv2.VideoCapture(0)
    #cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 1920)      # <-- this doesn't work. OpenCV tries to set VIDIO_S_CROP instead of the frame format
    #cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 1080)
    
    # The following is from: https://github.com/gebart/python-v4l2capture
    
    # Open the video device.
    video1 = v4l2capture.Video_device("/dev/video2")
    
    c = v4l2.v4l2_control()
    c.id = v4l2.V4L2_CID_EXPOSURE_ABSOLUTE
    c.value = 50
    fcntl.ioctl(video1, v4l2.VIDIOC_S_CTRL, c)

    time.sleep(1)
    # Suggest an image size to the device. The device may choose and
    # return another size if it doesn't support the suggested one.
    size_x, size_y = video1.set_format(1280, 960, 1)
    
    print "device chose {0}x{1} res".format(size_x, size_y)
    
    # Create a buffer to store image data in. This must be done before
    # calling 'start' if v4l2capture is compiled with libv4l2. Otherwise
    # raises IOError.
    video1.create_buffers(1)
    
    # Send the buffer to the device. Some devices require this to be done
    # before calling 'start'.
    video1.queue_all_buffers()

    
    # Start the device. This lights the LED if it's a camera that has one.
    print "start capture"
    video1.start()
    count = 0
    while(True):
        print("waiting for buffer")
        select.select((video1,), (), ())
        print("buffer full")
        image_data1 = video1.read_and_queue()
        
        frame1 = np.fromstring(image_data1, np.uint8).reshape(960,1280)
        cv2.imwrite(str(count) + ".png", frame1)
        count = count +1
        #cv2.imshow('frame1', frame1)
        #key = cv2.waitKey(1)
        #if key & 0xFF == ord('q'):
        #    break

    video1.close()
    
    cv2.destroyAllWindows()