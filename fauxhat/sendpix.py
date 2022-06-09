#import pygame, sys
import sys
import io
#from pygame.locals import *
#import pygame.camera
import os
import time
import datetime
from sense_hat import SenseHat
import websocket
from time import process_time
import urllib.request
#from netifaces import interfaces, ifaddresses, AF_INET
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageShow

#useful constant
my_version=':v14Apr2022:'
ds = u'\N{DEGREE SIGN}'
pq='5' #png compression factor (0-9)
angle = 180
#CPU_T_FACTOR = 0#1.5558


image_dir=os.getenv("IMAGE_DIR",os.path.expanduser('~')+'/Pictures')

if not (os.path.exists(image_dir)):
    print('creating top-level directory', image_dir)
    os.system('mkdir '+image_dir)
else:
    print("using image directory",image_dir)

imageUploadURL=os.getenv("ImageUploadURL",default="http://edgepilognodered2021.mybluemix.net/detect")
webSocketURL=os.getenv("WebSocketURL",     default="wss://edgepilognodered2021.mybluemix.net/ws/chat")

nodeName = os.getenv("NODE_NAME", default="rpi4-hat")
chat_user = os.getenv("CHAT_USER", default=nodeName.split('.')[0])
chat_user = chat_user+'-sendpix'
#motioneye_host = "http://motioneye-service.camshare.svc.cluster.local:8765"
#UPDATED 14 April 2022 -- cluster automatically inserts service host IP address as an environment variable, use that
motioneye_host = os.getenv("MOTIONEYE_SERVICE_SERVICE_HOST",     default="motioneye-service.camshare.svc.cluster.local"    )
# now add protocol and port
motioneye_host = "http://" + motioneye_host + ":8765"
camangle= os.getenv("CameraAngle", default="180")
cpu_TF = os.getenv("CPUTF", default="1.5558")
CPU_T_FACTOR = float(cpu_TF)


motioneye_snapURL=motioneye_host + "/picture/1/current/"
myimage_file=image_dir+'/101.png'

videoSource=os.getenv("VideoSource",default="/dev/video0")





#-------------------------------------------se
# read the cpu temperature
#-------------------------------------------
def cpu_temp():
    f = open("/sys/class/thermal/thermal_zone0/temp", "r")
    cpu_temp=float(f.readline())/1000
    f.close()
    print("CPU Temp:",cpu_temp)
    return cpu_temp

#--------------------------------
# return temp corrected for CPU temp heating
#--------------------------------
def corrected_temp(temp):
    global CPU_T_FACTOR
    #temp=hat.get_temperature()
    if CPU_T_FACTOR != 0:
        corrected_temp = temp - ((cpu_temp() - temp)/CPU_T_FACTOR)
    else:
        corrected_temp = temp
    #print("raw temp:",temp," | corrected temperature:" , corrected_temp  )  
    return corrected_temp
    
    



#--------------------------------------------
# Send a message to the chat
#--------------------------------------------
def sendchat(message):
    global ws
    try:
        print(message)
        ws.send(message)
    except (BrokenPipeError,websocket._exceptions.WebSocketConnectionClosedException) as e:
        try:
            ws.connect(webSocketURL)
            ws.send(message)
        except (BrokenPipeError,websocket._exceptions.WebSocketBadStatusException,websocket._exceptions.WebSocketConnectionClosedException) as e:
            print("Cannot send to Web Socket, Ignored")



#----------------------------------------------------------------
# Set the LED display size and rotation
#----------------------------------------------------------------
def orient(hat):
    global angle
    acceleration = hat.get_accelerometer_raw()
    x = acceleration['x']
    y = acceleration['y']
    z = acceleration['z']
    x=round(x, 0)
    y=round(y, 0)
    z=round(z, 0)
    print("current acceleration: ",x,y,z)

    if y == -1:
        angle = 180
    elif y == 1:
        angle = 0
    elif x == -1:
        angle = 90
    elif x == 1:
        angle = 270
    #else:
        #angle = 180
    print("angle selected:",angle)
    hat.set_rotation(angle)

#-----------------------------------------------------------------------------------
# annotate and save image
# -------------------------------------------------------------------
def annotate_image(img, title='', subtitle='', marker='', save_path=''):
    # Read the image
    #img = Image.open(image_file)
    height=img.size[1]
    width=img.size[0]
    # Create an image drawing object
    imageChyron = ImageDraw.Draw(img,'RGBA')
    # Add the chyron bar
    imageChyron.rectangle([(0,int(.9*height)),(width,height)],fill=(0,0,255,125))
    #load a better font
    font=ImageFont.truetype(font='fonts/NimbusSans-Bold.otf', size=36)
    #add the title and subtitle
    imageChyron.multiline_text( \
                (int(.02*width),int(.915*height)), \
                title +"\n" \
                + subtitle , \
                fill = (255,255,255), font = font, spacing = int(.02*height))
    #add the file marker (usually TS and some string)
    imageChyron.multiline_text( \
                (int(.99*width),int(.995*height)), \
                marker, \
                fill = (255,255,255), font = font, spacing = int(.02*height), \
                anchor='rd') #positions lower right corner of marker
    img.save(save_path)



#----------------------------------------------------------------------
# take SenseHat environmental data, grab and label a frame with fscamera and save it to the USB storage
#----------------------------------------------------------------------

def take_pic_with_data(sh,image_path):
    #formatting strings
    hat_data = "Temp: {t:.2f}"+ds+"C | RelHum: {h:.2f}% | Press: {p:.1f}mbar | Compass: {o:.2f}"+ds
    hat_gyro = "Roll: {r:.1f}"+ds+"| Pitch {pt:.2f}"+ds+"|Yaw {y:.1f}"+ds

    #get sensor data
    temperature=corrected_temp(sh.get_temperature())
    humidity=sh.get_humidity()
    orient = sh.get_compass()
    press = sh.get_pressure()
    gyro = sh.get_gyroscope()
    roll = gyro['roll']
    pitch = gyro['pitch']
    yaw = gyro['yaw']

    print('Taking photo')
    p_rot=os.getenv("CAM_ROTATION","0")    # try getting any rotation from environment
    timenow=datetime.datetime.now()
    tstamp=timenow.strftime('%H%M%S')
    marker=timenow.strftime('%Y-%m-%d | %H:%M:%S')

    try:
        urllib.request.urlretrieve(motioneye_snapURL,'100.png')
        print("image "+image_path +" saved")
    except:
        message='{"user":"'+chat_user+my_version+'","message":" problem retrieving image from:'+motioneye_snapURL+'"}'
    else:
        myimage=Image.open('100.png')
        annotate_image(myimage, \
                    hat_data.format(t=temperature,h=humidity,p=press,o=orient), \
                    hat_gyro.format(r=roll,pt=pitch,y=yaw), \
                    marker, \
                    image_path)     # uses Fswebcam to take picture
        
        

#----------------------------------------------------------------------------------
#   use set_pixels for a non-blocking temperature display
#--------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------------------------------------------------------
# function to build the list for -99 to 99
#--------------------------------------------
def build_digits(numvalue, b='b', w='w'):
    global digits
    numstring=str(int(abs(numvalue)))
    #w = 'w'#[0, 00, 255]  # Blue
    #b = 'b'#[0, 0, 0]  # Black
    sign_ind=[b]
    digits ={    
        'd0' : [b,w,w,w,
                b,w,b,w,
                b,w,b,w,
                b,w,b,w,
                b,w,w,w],
        'd1' : [b,b,w,b,
                b,w,w,b,
                b,b,w,b,
                b,b,w,b,
                b,w,w,w],
        'd2' : [b,w,w,w,b,b,b,w,b,w,w,w,b,w,b,b,b,w,w,w],
        'd3' : [b,w,w,w,b,b,b,w,b,w,w,w,b,b,b,w,b,w,w,w],
        'd4' : [b,w,b,b,b,w,b,b,b,w,w,b,b,w,w,w,b,b,w,b],
        'd5' : [b,w,w,w,b,w,b,b,b,w,w,w,b,b,b,w,b,w,w,w],
        'd6' : [b,w,w,w,b,w,b,b,b,w,w,w,b,w,b,w,b,w,w,w],
        'd7' : [b,w,w,w,b,b,b,w,b,b,b,w,b,b,b,w,b,b,b,w],
        'd8' : [b,w,w,w,b,w,b,w,b,w,w,w,b,w,b,w,b,w,w,w],
        'd9' : [b,w,w,w,b,w,b,w,b,w,w,w,b,b,b,w,b,b,b,w],
        'bl' : [b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b]}
    if abs(numvalue) < 10:
        first_digit=digits['bl']
        second_digit=digits['d'+numstring[0]]
    else:
        if abs(numvalue) < 100:
            first_digit=digits['d'+numstring[0]]
            second_digit=digits['d'+numstring[1]]
        else:
            first_digit = digits['d9']
            second_digit = digits['d9']
       
    if numvalue<0:    #  add a minus sign indicator if required
        sign_ind=[w]
    else:
        sign_ind=[b]
        
    out_digits= first_digit[:4]+second_digit[:4]+ \
                sign_ind + \
                first_digit[5:8] + second_digit[4:8] + \
                first_digit[8:12] + second_digit[8:12] + \
                first_digit[12:16] + second_digit[12:16] + \
                first_digit[16:20] + second_digit[16:20]

    return out_digits#, first_digit, second_digit
                        
                        

        


#----------------------------------------------------------------
# show the temperature on the led array
#----------------------------------------------------------------

def show_temp(hat,newtemp):
    w = [0, 00, 255]  # Blue
    b = [0, 0, 0]  # Black
    #first two pixels are used elsewhere for status indicators, so grab their colors to be able to restore them
    pixel00=hat.get_pixel(0,0)
    pixel01=hat.get_pixel(1,0)
    pixel02=hat.get_pixel(2,0)
    numb='tLO'
    blank = [b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b,b] # will be used to have different first three lines depending on pressure readings etc
    degree = [b,b,b,b,b,b,w,w,b,b,b,b,b,b,w,w,b,b,b,b,b,b,b,b]
    pnum ={
    'tLO' : [b,w,b,b,b,w,w,w,b,w,b,b,b,w,b,w,b,w,b,b,b,w,b,w,b,w,b,b,b,w,b,w,b,w,w,w,b,w,w,w],
    'tHI' : [b,w,b,w,b,w,w,w,b,w,b,w,b,b,w,b,b,w,w,w,b,b,w,b,b,w,b,w,b,b,w,b,b,w,b,w,b,w,w,w]}
    orient(hat)
    print('trying to display temperature',int(newtemp))
    
    if newtemp >= -99:
        if newtemp < 100:
            all_pixels = degree + build_digits(newtemp, b, w)
        else:
            numb = "tHI"
            all_pixels = degree + pnum[numb]
    else: # (newtemp < -99):
        numb = "tLO"
        all_pixels = degree + pnum[numb]
    try:
        hat.set_pixels (all_pixels)
    except:
        numb = numb
        
    print("displaying index",numb," for temperature",newtemp)
    #reset the first two pixels
    hat.set_pixel(0,0,pixel00)
    hat.set_pixel(1,0,pixel01)
    hat.set_pixel(2,0,pixel02)
    
print("connecting to nodered")
#websocket.enableTrace(True)
ws = websocket.WebSocket()
try:
    ws.connect(webSocketURL)
except websocket._exceptions.WebSocketBadStatusException as e:
    print("Cannot connect to Web socket")

    


sense = SenseHat()
Looping = True

waittime=1

while Looping: # do forever
    tstr=datetime.datetime.now().strftime('%H:%M:%S')
    sense.set_pixel(0,0,(255,0,0))

    message='{"user":"'+chat_user+my_version+'","message":"'+tstr+': Taking Photo"}'
    sendchat(message)
    take_pic_with_data(sense,myimage_file)
    print("uploading photo")
    upload_cmd="curl -F myFile=@"+myimage_file+" -F submit=Submit "+imageUploadURL
    try:
        print("trying",upload_cmd)
        os.system(upload_cmd)
    except:
        print("problem uploading image")
        
 
    sense.set_pixel(0,0,(0,255,0))
    tstr=datetime.datetime.now().strftime('%H:%M:%S')
    temp = sense.get_temperature()
 
    temp = corrected_temp(temp)
    show_temp(sense,temp)
    temp_str=("Temperature: %.2f" % temp) +ds+"C"
 
    message='{"user":"'+chat_user+my_version+'","message":"'+tstr+': %s"}'% temp_str
    print(message)
    sense.set_pixel(0,0,(0,0,255))
    sendchat(message)

    print('waiting %d seconds...' % waittime)
    goAgain = False
    myTimer=process_time()
    while not goAgain:
      for event in sense.stick.get_events():   
         if event.action == 'held' and event.direction =='middle':
            print('shutdown option disabled') #shutdown=True 
         if event.action == 'held' and event.direction !='middle':
            Looping = False
            goAgain = True
            break
         if event.action == 'pressed':      #somebody tapped the joystick -- go now
            goAgain=True
      if (process_time()-myTimer>waittime):       # 10 seconds elapsed -- go now
            goAgain=True


print("Program Execution ended normally")
