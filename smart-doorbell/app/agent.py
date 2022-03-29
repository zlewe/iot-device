import paho.mqtt.client as mqtt
import subprocess
import requests
import time
import threading
import json
import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime

def lockup():
    global locked,led_pin,last_lock_time
    locked = 1
    GPIO.output(led_pin, GPIO.HIGH)
    print('=============')
    print('=============')
    print('Locked again!')
    print('=============')
    print('=============')
    
def unlock():
    global locked,led_pin,last_lock_time
    locked = 0
    last_lock_time = datetime.now()
    GPIO.output(led_pin, GPIO.LOW)
    print('===================')
    print('===================')
    print('Banidesin UNLocked!')
    print('===================')
    print('===================')

def on_connect(client, userdata, flags, rc):
	print("Connect to the broker")
	client.subscribe('device/'+serial)

def on_message(client, userdata, msg):
    global locked,serial,last_lock_time
    
    if msg.payload==b'unlock' and locked==1:
        unlock()

def getSerial():
	serial = "ERROR00000000000"
	try:
		f=open('/proc/cpuinfo','r')
		for line in f:
			if line[0:6]=='Serial':
				serial=line[18:25]
				break
		f.close()
	except:
		print("ERROR: Failed to get the serial number!")
	return serial

def ffmpeg():
    subprocess.run(['ffmpeg', '-f','lavfi',
    '-i','anullsrc=channel_layout=stereo:sample_rate=44100',
'-f','v4l2','-i','/dev/video0','-c:v','libx264','-pix_fmt','yuv420p',
'-preset','ultrafast','-g','10','-b:v','100k','-bufsize','512k',
'-threads','2','-qscale','3','-b:a','96k','-r','10','-s','640x360',
'-f','flv',f'{rtmp_server}{serial}'], stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)

locked = 1
button_pin=16
led_pin=18

api=''
rtmp_server='rtmp://0.tcp.ap.ngrok.io:14201'
mserver_ip='192.168.1.153'
mserver_port=1883

password = 'asshole'
access_token = ''
refresh_token = ''
last_lock_time=datetime.now()

if __name__ == '__main__':
    
    serial = getSerial()
    print(f'#####The serial number is {serial}#####')
    
    print('Try to get host names...')
    while True:
        try:
            r = requests.get('https://brianswebapp.herokuapp.com/getHostName')
            if r.status_code>=200 and r.status_code<300:
                print(f'Get Host Names:{r.text}')
                names = json.loads(r.text)
                api = names['api']
                rtmp_server = names['rtmp']
                mserver_ip = names['mqtt']
                mserver_port = names['mqtt_port']
                
                print(f'Change rtmp server to {rtmp_server}')
                print(f'Change mqtt server to {mserver_ip}:{mserver_port}')
                break
        
        except:
            print('ERROR {r.status_code}: Failed to get server name!')
            
        print('Retry connection after 1 sec...')
        time.sleep(1)
        
    print('Try to connect mqtt server...')
    while True:
        try:
            mclient = mqtt.Client(client_id=serial)
            mclient.on_connect = on_connect
            mclient.on_message = on_message
            mclient.connect(mserver_ip, int(mserver_port))
            break
        except:
            print('ERROR: Failed to connect mqtt server!')
            
        print('Retry connection after 1 sec...')
        time.sleep(1)
        
    print('Try to get login the device...')
    while True:
        try:
            r = requests.post(f'{api}login/device?serial={serial}&passw={password}')
            if r.status_code>=200 and r.status_code<300:
                resp = json.loads(r.text)
                access_token = resp['access_token']
                refresh_token = resp['refresh_token']
                print(resp['message'])
                break        
        except:
            print(f'ERROR {r.status_code}: Failed to login this device!')
            
        print('Retry connection after 1 sec...')
        time.sleep(1)
    
    print('Start streamimg!')
    ffmpeg_thread = threading.Thread(target = ffmpeg)
    ffmpeg_thread.start()
    
    #mclient.loop_forever()
    
    print('Initialize GPIO...')
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(led_pin, GPIO.OUT)
    GPIO.output(led_pin, GPIO.HIGH)
    
    count = 0
    while True:
        mclient.loop()
        
        count+=1
        if count>20:
            try:
                mclient.reconnect()
            except:
                time.sleep(1)
            count=0
               
        try:
            if count==0:
                headers = {"Authorization":f'Bearer {refresh_token}'}
                r = requests.post(f'{api}token/refresh', headers=headers, timeout=3)
                if r.status_code>=200 and r.status_code<300:
                    resp = json.loads(r.text)
                    access_token = resp['access_token']
                    print(resp['message'])
            
            headers = {"Authorization":f'Bearer {access_token}'}
            r = requests.get(f'{api}whisper?serial={serial}&lock_status={locked}', headers=headers, timeout=3)
            print(f'whisper with result:{r.status_code}')
        except:
            print('Could be timeout!')
        
        button = GPIO.input(button_pin)
        if button==0:

            print('===================')
            print('===================')
            print('Knock!!!  Knock!!!!')
            print('===================')
            print('===================')
            now = datetime.now().isoformat()
            
            while True:
                try:
                    r = requests.get(f'{api}knock?serial={serial}&time={now}', headers=headers, timeout=3)
                    break
                except:
                    pass
        if locked==0 and (datetime.now() - last_lock_time).total_seconds() > 10:
            lockup()
            
        if ffmpeg_thread.is_alive() == False:
            print('FFmpeg just died! Restart a streaming thread...')
            ffmpeg_thread = threading.Thread(target = ffmpeg)
            ffmpeg_thread.start()
        
    