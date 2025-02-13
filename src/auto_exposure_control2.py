#!/usr/bin/env python

"""
auto_exposure_control.py subscribes to a ROS image topic and performs
histogram based automatic exposure control based on the paper
"Automatic Camera Exposure Control", N. Nourani-Vatani, J. Roberts
"""
#import roslib
import math
import numpy as np
import cv2
import sys
import rospy
from sensor_msgs.msg import Image, CompressedImage
from std_msgs.msg import Float32
from cv_bridge import CvBridge, CvBridgeError
import dynamic_reconfigure.client

# I term for PI controller
err_i = 0
exp_cur = 0
pub_exposure=rospy.Publisher('/telicam/set_exposure', Float32, queue_size=3)
output = 0

# def get_exposure(dyn_client):
#     values = dyn_client.get_configuration()
#     return values['exposure_value']

# def set_exposure(dyn_client, exposure):
#     params = {'exposure_value' : exposure}
#     config = dyn_client.update_configuration(params)

def exp_callback(msg):
    global exp_cur
    exp_cur = msg.data

def image_callback(image, args):
    global err_i
    global exp_cur
    global pub_exposure
    global output
    bridge = args['cv_bridge']
    # dyn_client = args['dyn_client']
    # cv_image = bridge.imgmsg_to_cv2(image,
                                    # desired_encoding = "bgr8")
    cv_image = bridge.compressed_imgmsg_to_cv2(image,
                                    desired_encoding = "bgr8")
    
    (rows, cols, channels) = cv_image.shape
    if (channels == 3):
        brightness_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)[:,:,2]
    else:
        brightness_image = cv_image

    #crop_size = 10
    #brightness_image = brightness_image[rows-crop_size:rows+crop_size, cols-crop_size:cols+crop_size]

    #(rows, cols) = brightness_image.shape
    
    hist = cv2.calcHist([brightness_image],[0],None,[5],[0,256])
    
    mean_sample_value = 0
    for i in range(len(hist)):
        mean_sample_value += hist[i]*(i+1)
        
    mean_sample_value /= (rows*cols)
    print("MSV: {}".format(mean_sample_value))
    #focus_region = brightness_image[rows/2-10:rows/2+10, cols/2-10:cols/2+10]
    #brightness_value = numpy.mean(focus_region)

    # Middle value MSV is 2.5, range is 0-5
    # Note: You may need to retune the PI gains if you change this
    desired_msv = 2.5
    # Gains
    k_p = 0.05 # 0.05
    k_i = 0.01 # 0.01
    # Maximum integral value
    max_i = 3
    err_p = desired_msv-mean_sample_value
    err_i += err_p
    if abs(err_i) > max_i:
        err_i = np.sign(err_i)*max_i
    
    # Don't change exposure if we're close enough. Changing too often slows
    # down the data rate of the camera.
    if abs(err_p) > 0.5:
        # set_exposure(dyn_client, get_exposure(dyn_client)+k_p*err_p+k_i*err_i)
        output = exp_cur + (k_p*err_p+k_i*err_i) * 1000
        if output < 18.0:
            output = 18
        elif output > 160000.0:
            output = 160000.0
        pub_exposure.publish(output)
    print("change exposure: {}".format(output))
    print("-----")
        
def main(args):
    rospy.init_node('auto_exposure_control')

    bridge = CvBridge()
    # camera_name = rospy.get_param('~camera_name')
    # dyn_client = dynamic_reconfigure.client.Client(camera_name)

    # params = {'auto_exposure' : False}
    # config = dyn_client.update_configuration(params)
    
    args = {}
    args['cv_bridge'] = bridge
    # args['dyn_client'] = dyn_client
    # img_sub=rospy.Subscriber('/camera/image_color', Image, image_callback, args)
    img_sub=rospy.Subscriber('/teli_camera/image_raw/compressed', CompressedImage, image_callback, args)
    exp_sub=rospy.Subscriber('/telicam/exposure', Float32, exp_callback)
    

    rospy.spin()
    
if __name__ == "__main__":
    try:
        main(sys.argv)
    except rospy.ROSInterruptException: pass