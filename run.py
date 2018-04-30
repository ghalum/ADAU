#!/usr/bin/python3

####################################
# Avian Data Acquisition Unit
# Author: Nicholas Daniels
# Last Revision: 12-12-2017
####################################
from picamera import PiCamera	# Import PiCamera module
from picamera import Color	# Import color for camera annotations
from scale import Scale		# Import HX711 modified scale library: For some reason I never set the pin location in the main code. Set pin location here or change it.
import RPi.GPIO as GPIO		# Import Pi GPIO library
import datetime			# Import date and time library
import dht22			# Import dht22 sensor library
import csv			# Import CSV library
import os			# Import Operating System library for file path help
import sys			# Import system library for exception catching
import schedule			# Allows us to schedule a function every 30s
from statistics import mean	# Lazy way to find the average. 

class FixedlenList(list):
    def __init__(self,l=0):
        super(FixedlenList,self).__init__()
        self.__length__=l #fixed length
       
    def pop(self,index=-1):
        super(FixedlenList, self).pop(index)
   
    def remove(self,item):
        self.__delitem__(item)
       
    def __delitem__(self,item):
        super(FixedlenList, self).__delitem__(item)
        #self.__length__-=1
       
    def append(self,item):
        if len(self) >= self.__length__:
            super(FixedlenList, self).pop(0)
        super(FixedlenList, self).append(item)     
   
    def extend(self,aList):
        super(FixedlenList, self).extend(aList)
        self.__delslice__(0,len(self)-self.__length__)
 
    def insert(self):
        pass
 
# This is the list of average values, could be adjusted, but 25 values seems to work okay.
movingList = FixedlenList(25)

# Defining variable for getting current time
#timeNow = datetime.datetime.now()

# Setting the temperature and humidity sensor to GPIO pin 4
instance = dht22.DHT22(pin=4)

# Define folder paths for saving the data
dpath = "/media/pi/USB2/logs/" + datetime.datetime.now().strftime("%m-%d-%Y") # Defines location to save data on USB stick, names folder based on current date
datapath = os.path.abspath(dpath) # Appends the logs folder location to system root directory. 
csvname = datetime.datetime.now().strftime("%-I.%M.%S_%d-%m-%Y") + ".csv"  # CSV name as time then date
csvLocation = os.path.abspath(dpath + "/" + csvname) # Defines location to save CSV file, todays date folder
videopath = os.path.abspath(dpath + "/video/") # Defines location to save raw video file, todays date, and then video folder

# If folders don't exist for data collection, create them, otherwise do nothing.
if not os.path.exists(videopath):
    os.makedirs(videopath)
    
if not os.path.exists(datapath):
    os.makedirs(datapath)
     
# Define camera variable and its settings
camera = PiCamera()
camera.rotation = 0
camera.resolution = (1296, 730)
camera.framerate = 30
camera.annotate_foreground = Color('white')
camera.annotate_background = Color('black')
cameraAnnoSize = 50
    
# Load the scale and tare it
scale = Scale() # Turns the scale on
scale.setReferenceUnit(4001.7805) # Calibration factor for load-cell
scale.reset() # Resets the HX711 chip
scale.tare() # Tares the load-cell - Sets output to zero.
scale.reset() # Resets the HX711 chip
scale.tare() # Tares the load-cell - Sets output to zero.

# Turn on LED
GPIO.setup(26, GPIO.OUT)
GPIO.output(26,True)

print ("Scale ready...") # Prints a ready to terminal for debugging

# Open a new CSV file, naming and storing it as defined above
with open(csvLocation, "w", newline="") as csvfile:
	
	# Create CSV header, 1st row entries
	fieldnames = ["time", "mass", "temp", "humid"] # Defining the columns in the first row
	c = csv.DictWriter(csvfile, fieldnames=fieldnames) # Set the header 
	c.writeheader()	# Write the header into the CSV
	
	# Start recording the video in the specified path, named as specified
	# Once the camera has started, annotate it with the time.
	camera.start_recording(os.path.abspath(dpath + "/video/" \
				+ datetime.datetime.now().strftime("%-I.%M.%S_%m-%d-%Y")  + ".h264") )
											
	camera.annotate_text = datetime.datetime.now().strftime("%H:%M:%S") # Write current time to camera annotation
	camera.annotate_text_size = cameraAnnoSize # Set annotation to predefined size
	
	# Initalize values for temperature and humidity
	temp = 0.0
	humid = 0.0
	
	# Every 30s this function is being called. If the average number of values in the list is less than 1, tare the scale twice.
	# Seems to work better with a second tare.
	def timedTare():
		if mean(movingList) < 1:
			scale.reset()
			scale.tare()
			scale.reset()
			scale.tare()
			
	# Every 30s jump to timedTare function
	schedule.every(30).seconds.do(timedTare)
	
	# Enter the main running loop
	while True:
		# Points to the 30 seccond timer above. It remembers to check the time for the scheduled interrupt.
		schedule.run_pending()
		# Unless an exception occurs, run this code
		try:
			# Call for a scale, temperature, and humidity reading
			scaleReading = scale.getMeasure()
			dhtReading = instance.read()
			
			# If the dht reading is valid, store it as a new temp and humid value
			if dhtReading.is_valid():
				temp = dhtReading.temperature
				humid = dhtReading.humidity 
			
			# Update camera annotation with mass, temp, and humid
			annotation = datetime.datetime.now().strftime("%H:%M:%S " \
						+ "Mass: " + str("{0:.1f}".format(scaleReading)) + "g " \
						+ "T: " + str("{0:.1f}".format(temp)) + " F " \
						+ "H: " + str("{0:.1f}".format(humid)) + "%%" \
						)
						
			camera.annotate_text = annotation
			camera.annotate_text_size = cameraAnnoSize
			
			# If the scale reading is within the desired range perform the following
			if scaleReading > -10:
				
				# The if and else statements capture the scale value and record it to the CSV file and update the camera annotation
				# The if statement looks to see if the temperature and humidity value is valid, if it is it will record it into the CSV
				# If the DHT reading is not valid, it exclude it from the CSV to conserve memory, but will still record a load-cell reading
				
				if dhtReading.is_valid():
					
					temp = dhtReading.temperature
					humid = dhtReading.humidity 
					if scaleReading > 1 :
						c.writerow({'time': datetime.datetime.now().strftime("%H:%M:%S"), \
									'mass': str("{0:.1f}".format(scaleReading)), \
									'temp': str(temp), \
									'humid': str(humid) \
									})
								
					print(str("{0:.1f}".format(scaleReading)) + ' g')
					camera.annotate_text = annotation
					camera.annotate_text_size = cameraAnnoSize
					scaleReading = scale.getMeasure()
					movingList.append(scaleReading)
					
				else:
					if scaleReading > 1:
						c.writerow({'time': datetime.datetime.now().strftime("%H:%M:%S"), \
									'mass': str("{0:.1f}".format(scaleReading)) \
									})
								
					print(str("{0:.1f}".format(scaleReading)) + ' g')
					camera.annotate_text = annotation
					camera.annotate_text_size = cameraAnnoSize
					scaleReading = scale.getMeasure()
					movingList.append(scaleReading)
		
		# An exception occured, run this code instead
		# Resets the GPIO pins, stops the camera, and exits the code
		except (KeyboardInterrupt, SystemExit):
			GPIO.cleanup()
			camera.stop_recording()
			sys.exit()			
