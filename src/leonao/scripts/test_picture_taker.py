#!/usr/bin/env python
## Example to setup the frameworks for the canvas

import rospy
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

from naoqi import ALProxy

from naoqi_bridge_msgs.msg import HeadTouch


USE_MEDIA_PIPE_DIRECT = False

WATCHFOLDER_PATH = "/home/hrsa/watchfolder/"

# Image Rotations: 
# cv2.ROTATE_90_COUNTERCLOCKWISE
# cv2.ROTATE_180
# cv2.ROTATE_90_CLOCKWISE

IMAGE_ROTATION = cv2.ROTATE_90_COUNTERCLOCKWISE

if USE_MEDIA_PIPE_DIRECT:
    from face_detector import FaceDetector
# The picture taker module is responsible for taking pictures
## The module should provide for the following tasks as seperate functions:
## Tell the model that the picture will be taken
## Take a picture and save it
## Analse the picture if it is of high enough quality and return the result (how the picture can be improved)
### Try to find a face in the picture

class pictureTaker:
    def __init__(self, local = False):
        self.local = local
        if local:
            self.camera = cv2.VideoCapture(0)
        self.minFaceSize = 0.33
        self.minBrightness = 100
        self.maxBrightness = 200
        self.minContrast = 50
        self.front_button_pressed = False
        # Might have to change later
        if not self.local:
            import rospy
            from sensor_msgs.msg import Image
            from cv_bridge import CvBridge
            self.robot_ip=str(os.getenv("NAO_IP"))
            self.robot_port=int(9559)

            self.tts = ALProxy("ALTextToSpeech", self.robot_ip, 9559)

            #self.head_sub = rospy.Subscriber('/tactile_touch', HeadTouch, self.head_touch_callback)
            #self.front_button_pressed = False
            self.bridge = CvBridge()
            self.image_sub = rospy.Subscriber("/nao_robot/camera/top/camera/image_raw", Image, self.newImageCallback)
            self.head_sub = rospy.Subscriber('/tactile_touch', HeadTouch, self.head_touch_callback)

            print("initialized")


    def takePicture(self, path, img_msg = None):
        if self.local:
            ret, frame = self.camera.read()
            cv2.imwrite(path, frame)
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            # Convert raw image data to cv mat BGR8
            img = self.bridge.imgmsg_to_cv2(self.currentImageFromStream, desired_encoding='bgr8')

            if IMAGE_ROTATION:
                img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)


            with open(WATCHFOLDER_PATH + "result.txt", "w") as f:
                f.write("")
            cv2.imwrite(WATCHFOLDER_PATH+path, img)  
            print("Path", os.path.abspath("."), path)
            print("Image saved")
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    def analyzePicture(self, img, showAnalysis = False):
        # Show the picture with pyplot if showAnalysis is True
        if showAnalysis and False:
            print("I will show you what I got")
            plt.imshow(img)
            plt.xticks([]), plt.yticks([])
            plt.show()

        # Analyze the picture and return the result
        # try to find a face in the picture
        if USE_MEDIA_PIPE_DIRECT:
            faceDetector = FaceDetector()
            bbox, _ = faceDetector.detect_face(img)
            print(bbox)
            print(type(bbox))
        else:
            # Read the result.txt file in watchfolder
            # The result.txt file contains the result of the face detection
            bbox = ""
            while bbox == "":
                with open(WATCHFOLDER_PATH + "result.txt", "r") as f:
                    bbox = f.read()
                    if bbox == "None":
                        bbox = np.array(None)
                        break
                    if bbox == "":
                        continue
                    bbox = bbox.replace("[  ", "")
                    bbox = bbox.replace("[ ", "")
                    bbox = bbox.replace("[", "")
                    bbox = bbox.replace("]", "")
                    bbox = bbox.replace("  ", " ")
                    bbox = bbox.split(" ")
                    print(bbox)
                    bbox = [int(i) for i in bbox]
                    bbox = np.array(bbox)
                    print(bbox)

        if (bbox == None).any():
            self.speak("I could not see your face, there is probably too little contrast.")
            return "Error: No face found in picture", None
        
        # Check if the bounding box in bbox is large enough
        # should be at least 1/3 of the picture

        # Get the size of the picture
        imgHeight, imgWidth, imgChannels = img.shape
        # Get the size of the bounding box
        bboxMinSize = min(imgHeight, imgWidth) * self.minFaceSize
        #print(f'Face is {bbox[2]}x{bbox[3]} pixels, thats {bbox[2]/imgWidth*100}% of the width and {bbox[3]/imgHeight*100}% of the height')

        if bbox[2] < bboxMinSize or bbox[3] < bboxMinSize:
            self.speak("Face too small, please come closer")
            return "Error: Face too small, please come closer", None

        # Check if the face is too dark
        # Get the average brightness of the face   
        face = img[bbox[1]:bbox[1]+bbox[3], bbox[0]:bbox[0]+bbox[2]]
        faceBrightness = np.mean(face)
        #print(f'Face brightness is {faceBrightness}')
        if faceBrightness < self.minBrightness:
            self.speak("Face too dark, try to get more light")
            return "Error: Face too dark, try to get more light", None

        # Check if the face is too bright
        if faceBrightness > self.maxBrightness:
            self.speak("Face too bright, try to get less light")
            return "Error: Face too bright, try to get less light", None

        # Check if the face has too little contrast
        # Get the standard deviation of the face
        faceContrast = np.std(face)
       # print(f'Face contrast is {faceContrast}')
        if faceContrast < self.minContrast:
            self.speak("Face too little contrast, try to get more contrast")
            return "Error: Face too little contrast, try to get more contrast", None
        
        self.speak("Looks good!")
        return "Success", img

    def speak(self, text):
        print(text)
        self.tts.say(text)
        #os.system(f'say "{text}"')

    def main_loop(self):
        # Take a picture with the pictureTaker
        while not (self.front_button_pressed):
            rospy.sleep(0.2)
        self.speak("Taking a picture in 3, 2, 1 - smile!")
        img = self.takePicture("picture_to_analyze.jpg")
        analyzePictureResponse, img = self.analyzePicture(img, showAnalysis= True)
        if analyzePictureResponse == "Success":
            # Start creating the stylized image
            pass
        else:
            self.speak("Let's try again!")

    ################ Running Callbacks ################

    def head_touch_callback(self, head_touch_event):
        self.front_button_pressed = head_touch_event.button == HeadTouch.buttonFront and head_touch_event.state == HeadTouch.statePressed

    def newImageCallback(self, img_msg):
        
        #print("I received an image")
        self.currentImageFromStream = img_msg #TODO: Check for timing issues

if __name__ == '__main__':
    rospy.init_node('test_picture_taker', anonymous=False)
    pt = pictureTaker(local = False)
    try:
        while not rospy.is_shutdown():
            pt.main_loop()
            
    except rospy.ROSInterruptException:
        pass        



# Best practise using camera
# Subscriber buffer size one
# 
