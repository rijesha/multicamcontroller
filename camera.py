import v4l2capture
import select
import time
import v4l2
import fcntl
import logging
import numpy as np
import threading

class camera:
    def __init__(self, cam_data):
        self.disconnected = False
        self.frame = None
        self.running = True
        self.getNewFrameEvent = threading.Event()
        self.getNewFrameEvent.clear()

        self.gotNewFrameEvent = threading.Event()
        self.gotNewFrameEvent.clear()

        self.cam_data = cam_data
        self.video = v4l2capture.Video_device(cam_data['cam_location'])
        self.cam_num = str(cam_data["cam_num"])
        self.expo = cam_data["exposure_absolute"]
        self.bright = cam_data["brightness"]
        self.gain = 1
        self.privacy = cam_data["privacy"]

        self.centrefreq = str(cam_data["filter_centre(nm)"])
        self.freqBandwidth = str(cam_data["filter_BW(nm)"])
        self.cam_model = str(cam_data["cam_model"])
        self.hfv = str(cam_data["HFV (deg)"])
        self.vfv = str(cam_data["VFV (deg)"])


        size_x, size_y = self.video.set_format(1280, 960, 1)
        self.video.create_buffers(1)
        self.video.queue_all_buffers()

        self.update_gain(self.gain)
        self.update_exposure(self.expo)
        self.update_brightness(self.bright)
        self.update_privacy(self.privacy)
        self.update_frame_rate()

        self.video.start()


    def generateCamLogString(self):
        logstring = []
        logstring.append("cam_num: " + self.cam_num)
        logstring.append("centre_freq(nm): " + self.centrefreq)
        logstring.append("BW(nm): " + self.freqBandwidth)
        logstring.append("cam_model: " + self.cam_model)
        logstring.append("hfv (deg): " + self.hfv)
        logstring.append("vfv (deg): " + self.vfv)
        logstring.append("exposure: " + str(self.expo))
        logstring.append("gain: " + str(self.gain))
        return ','.join(logstring)
        
    def autoExpose(self, max_value):
        expo_time = self.expo
        if max_value > 220:
            expo_time = self.expo - 1
        elif max_value < 180:
            expo_time = self.expo + 1

        if expo_time > 20:
            expo_time = 20
        elif expo_time < 1:
            expo_time = 1
        
        if self.expo != expo_time:
            self.update_exposure(int(expo_time))
            self.expo = int(expo_time) 

    def update_gain(self, value):
        c = v4l2.v4l2_control()
        c.id = v4l2.V4L2_CID_GAIN
        c.value = value
        fcntl.ioctl(self.video, v4l2.VIDIOC_S_CTRL, c)

    def update_exposure(self, value):
        c = v4l2.v4l2_control()
        c.id = v4l2.V4L2_CID_EXPOSURE_ABSOLUTE
        c.value = value
        self.expo = value
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
        select.select((self.video.fileno(),), (), ())
        image_data = self.video.read_and_queue()
        logging.debug("read cam: " + self.cam_num + " with length of: " + str(len(image_data)))
        if len(image_data) != 1228800:
            print("FAILED " + self.cam_num + " -- retrying")
            logging.warning("FAILED " + self.cam_num + " -- retrying")
            if retry > 0 :
                return self.read(retry - 1)
            else :
                return None
        return np.fromstring(image_data, np.uint8).reshape(960,1280)

    def startCapturingThread(self):
        self.t = threading.Thread(target=self.frameRunner)
        self.t.start()

    def frameRunner(self):
        while self.running:
            self.getNewFrameEvent.wait()
            if not self.running:
                break
            self.getNewFrameEvent.clear()
            try:
                self.read_with_timeout()
            except IOError :
                self.disconnected = True
                self.gotNewFrameEvent.set()
                break
            
            self.gotNewFrameEvent.set()

    def triggerNewFrame(self):
        self.getNewFrameEvent.set()

    def getNewFrame(self):
        self.gotNewFrameEvent.wait()
        self.gotNewFrameEvent.clear()
        return self.frame

    def read_with_timeout(self, timeout = .500):
        output = select.select((self.video.fileno(),), (), (), timeout)
        if len(output[0]) == 0:
            print("timeout " + self.cam_num )
            logging.warning("timout cam: " + self.cam_num )
            self.frame = None
            return
        image_data = self.video.read_and_queue()
        
        if len(image_data) != 1228800:
            print("FAILED " + self.cam_num + " -- retrying")
            logging.warning("timout cam: " + self.cam_num )
            self.frame = None
        else:
            self.frame = np.fromstring(image_data, np.uint8).reshape(960,1280)

    def close(self):
        self.getNewFrameEvent.set()
        self.running = False
        self.video.stop()
        self.video.close()
