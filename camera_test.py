from picamera import PiCamera	#
import RPi.GPIO as GPIO	#
import picamera	#
import datetime	#
import time	#
import csv	#
import os	#
import sys	#
from picamera import Color

camera = PiCamera()
camera.rotation = 0
camera.resolution = (1920, 1080)
camera.framerate = 30

camera.start_preview()
camera.annotate_foreground = Color('white')
camera.annotate_background = Color('black')
camera.annotate_text = "Test"  
time.sleep(120)
camera.stop_preview()
