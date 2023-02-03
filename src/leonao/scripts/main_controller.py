#!/usr/bin/env python
## Main application controller

import rospy
import cv2

from naoqi_bridge_msgs.msg import HeadTouch
from sensor_msgs.msg import Image
from naoqi import ALProxy
from cv_bridge import CvBridge

import random

from enum import IntEnum
from picture_taker import *
from picture_painter import *

MSG_THANKS = "Thank you for visiting my studio, come back soon!"
MSG_BEFORE_SIESTA = "I am going to take a nap now. See you later!"

INTRO_MSG_1 = [
"Greetings! I am LeoNao Davinci, the mechanical artist.",
"Welcome to my workshop, where I create beautiful portraits just like Leonardo Da Vinci.",
"How do you do? I am LeoNao, a robot that paints portraits in the style of Leonardo Da Vinci.",
"Good day! I am LeoNao, a robot that emulates the famous Leonardo Da Vinci.",
"Salutations! I am LeoNao Davinci, a robot with the talent of Leonardo Da Vinci.",
"Step right up, step right up! I, the great Leonardo Da Vinci, am here to paint your portrait!"
]
INTRO_MSG_2 = [
"If you desire a stunning portrait, just press the button on my head",
"I would be honored to paint your portrait. Just touch my head to start.",
"Let's create a masterpiece together! Just press the button on my head.",
"Are you ready for a beautiful portrait? Simply touch the button on my head to begin.",
"It would be my pleasure to paint your portrait. Please touch the button on my head to start.",
"I can draw a masterpiece for you. Just come here and touch my head to start."
]
TAKING_PICTURE_INSTRUCTIONS_1 = [
"Perfect! Let's get started.",
"Excellent! Here we go!",
"Fantastic! Let's begin.",
"Great! I'm ready when you are.",
"Awesome! Let's make a masterpiece."
]
TAKING_PICTURE_INSTRUCTIONS_2 = [
"Please stand in front of me and hold still for the picture.",
"Get ready for your close-up! Stand in front of me and hold still."
"Just stand in front of me and stay still for the picture."
"Position yourself in front of me and hold still. I don't want to capture any movement."
"Take your place in front of me and hold still. I want to capture your true beauty.",
"Hold still, my friend! I don't want to capture your nerves, just your beauty."
]
MSG_BEFORE_PAINTING_START = [
"Wonderful! Now relax and let me paint your portrait.",
"Marvelous! I'll make sure you look even more stunning in the portrait.",
"Excellent! Just sit back and enjoy while I create your portrait.",
"Fantastic! I'll make sure to capture your best features in the portrait.",
"Superb! I'll bring out your beauty in the portrait.",
"Well done! please relax and enjoy while I paint you. Don't worry, I'll make you look better than you do in real life."
]
MSG_PICTURE_TAKEN_FAILED = [
"Oh dear, let's try again.",
"Darn, let's take the picture again.",
"Too bad, let's try taking the picture again.",
"Oh no, let's retry the picture.",
"Bummer, let's take the picture one more time."
]
MSG_PAINTING_IS_DONE = [
"It's finished! Here is your beautiful portrait! That will be 5 Euro, please.",
"Ta-da! Here is your stunning portrait! That will be 5 Euro, if you please.",
"Voila! Here is your gorgeous portrait! May I have 5 Euro, please?",
"Et voila! Here is your amazing portrait! That will be 5 Euro, thank you.",
"Behold! Here is your breathtaking portrait!"]


class Event(IntEnum):
    TAKE_PICTURE = 1
    PICTURE_SUCCESS = 2
    PICTURE_FAILED = 3
    PAINTING_DONE = 4

class State(IntEnum):
    IDLE = 1
    TAKING_PICTURE = 2
    PAINTING = 3

class Main_leonao_controller():
    def __init__(self):
        # FSM
        self.state = State.IDLE
        self.event = None
        self.idle_entered = False
        self.taking_picture_entered = False
        self.drawing_entered = False
        self.picture_taker =  pictureTaker(useTestPicture = False)
        self.picture_painter = Picture_painter()

        self.paths_file = SKETCH_FACE_PATHS_FILE
        #self.paths_file = WATCHFOLDER_PATH + "sergio_sketcher_result.pkl"

        # Events callbacks
        self.head_sub = rospy.Subscriber('/tactile_touch', HeadTouch, self.head_touch_callback)

        # Camera visualization
        self.bridge = CvBridge()
        imageTop = rospy.Subscriber("/nao_robot/camera/top/camera/image_raw", Image, self.showImageCallback)

        # Speak proxy
        robot_ip=str(os.getenv("NAO_IP"))
        robot_port=int(9559)
        self.tts = ALProxy("ALTextToSpeech", robot_ip, robot_port)
        self.speak(INTRO_MSG_1)
        self.speak(INTRO_MSG_2)

    def showImageCallback(self, img_msg):
        img = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        cv2.imshow("Current Image", img)
        cv2.waitKey(1)
    
    def speak(self, text, nonBlocking = False):
        if type(text) == str:
            if nonBlocking:
                self.tts.post.say("\\vol=100\\" + text + "\\pau=500\\")
            else:
                self.tts.say("\\vol=100\\" + text + "\\pau=500\\")
        elif type(text) == list:
            self.speak(random.choice(text))
        else:
            print("Speech input: " + text + " of type: " + type(text) + " not recognized!")
        
    def head_touch_callback(self, head_touch_event):
        if (head_touch_event.button == HeadTouch.buttonFront and head_touch_event.state == HeadTouch.statePressed):
            self.event = Event.TAKE_PICTURE
            self.check_event()

    def picture_event_callback(self, success):
        self.event = Event.PICTURE_SUCCESS if success else Event.PICTURE_FAILED
        self.check_event()

    def painting_event_callback(self):
        self.event = Event.PAINTING_DONE
        self.check_event()

    #def keyboard_event_callback(self):
    #    event = int(input("Enter event number: "))
    #    self.event = Event(event)
    #    self.check_event()

    def check_event(self):
        handled = False
        if self.state == State.IDLE:
            if self.event == Event.TAKE_PICTURE:
                self.state = State.TAKING_PICTURE
                self.idle_entered = False
                hanlded = True
        elif self.state == State.TAKING_PICTURE:
            if self.event == Event.PICTURE_SUCCESS:
                self.state = State.PAINTING
                self.taking_picture_entered = False
                hanlded = True
            elif self.event == Event.PICTURE_FAILED:
                self.speak(MSG_PICTURE_TAKEN_FAILED)
                self.state = State.IDLE
                self.taking_picture_entered = False
                hanlded = True
        elif self.state == State.PAINTING:
            if self.event == Event.PAINTING_DONE:
                self.speak(MSG_PAINTING_IS_DONE)
                self.speak(MSG_THANKS)
                self.state = State.IDLE
                self.drawing_entered = False
                hanlded = True
        
        if(hanlded == False):
            print("Invalid (state, event): ", self.state, self.event)

    def check_state(self):
        if self.state == State.IDLE:
            if self.idle_entered == False:
                self.idle_entered = True
                self.speak(INTRO_MSG_2)
            else:
                print("Waiting for the wake-up signal")
        elif self.state == State.TAKING_PICTURE:
            if self.taking_picture_entered == False:
                self.taking_picture_entered = True
                self.take_stylish_picture()
            else:
                print("Waiting for picture")
        elif self.state == State.PAINTING:
            if self.drawing_entered == False:
                self.drawing_entered = True
                self.draw_face()
            else:
                print("Waiting for drawing")
        else:
            print("Invalid state! ", self.state)

    def take_stylish_picture(self):
        self.speak(TAKING_PICTURE_INSTRUCTIONS_1)
        self.speak(TAKING_PICTURE_INSTRUCTIONS_2, nonBlocking=True)
        success = self.picture_taker.take_stylish_picture()
        #success = True
        self.picture_event_callback(success)
    
    def draw_face(self):
        self.speak(MSG_BEFORE_PAINTING_START)
        raw_input("press enter to draw")
        self.picture_painter.draw_face(self.paths_file)
        self.painting_event_callback()
                

if __name__ == '__main__':

    rospy.init_node('main_controller', anonymous=True)

    try:
        main_controller = Main_leonao_controller()
        #rate = rospy.Rate(10) # 10hz
        while not rospy.is_shutdown():
            main_controller.check_state()
            #print("Current state: ", main_controller.state)

    except rospy.ROSInterruptException:
        pass
