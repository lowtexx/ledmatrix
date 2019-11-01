# WS2812 LED Matrix by M Oehler
# https://hackaday.io/project/11064-raspberry-pi-retro-gaming-led-display
# Communication test script by lowtexx

TEST_MAX2719_DISPLAY=True
MAX2719_DISPLAYS=4 # number of cascaded displays
MAX2719_ORIENTATION=90 # Corrects block orientation when wired vertically choices=[0, 90, -90]
MAX2719_ROTATION=0 # Rotate display 0=0°, 1=90°, 2=180°, 3=270° choices=[0, 1, 2, 3]

#this script tests the communication to the Arduino
#clears the screen and tests setting individual pixels
#TODO Test receiving data

import serial # serial port to communicate to exernal Arduino
import time # sleep function
if TEST_MAX2719_DISPLAY:
    from luma.led_matrix.device import max7219
    from luma.core.interface.serial import spi, noop
    from luma.core.legacy import show_message, text
    from luma.core.render import canvas
    from luma.core.legacy.font import proportional, CP437_FONT
#    from luma.core.legacy import text, show_message
#    from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT

# only modify this two values for size adaption!
PIXEL_X=10
PIXEL_Y=20

#PORT_NAME = "/dev/ttyAMA0"
PORT_NAME = "/dev/ttyS0"

#some constants
COMMANDBYTE_DRAWPIXELRGB = 24
COMMANDBYTE_UPDATESCREEN = 30
COMMANDBYTE_CLEARSCREEN  = 32

#               R    G    B
WHITE       = (255, 255, 255)
GRAY        = (185, 185, 185)
BLACK       = (  0,   0,   0)
RED         = (255,   0,   0)
LIGHTRED    = (175,  20,  20)
GREEN       = (  0, 255,   0)
LIGHTGREEN  = ( 20, 175,  20)
BLUE        = (  0,   0, 255)
LIGHTBLUE   = ( 20,  20, 175)
YELLOW      = (255, 255,   0)
LIGHTYELLOW = (175, 175,  20)
CYAN        = (  0, 255, 255)
MAGENTA     = (255,   0, 255)
ORANGE      = (255, 100,   0)

COLORS      = (BLUE,GREEN,RED,YELLOW,CYAN,MAGENTA,ORANGE)


#TODO improve error handling when opening the port

serport=serial.Serial(PORT_NAME,baudrate=250000,timeout=3.0)




def clearScreen():
    serport.write(bytearray([COMMANDBYTE_CLEARSCREEN]))

def updateScreen():
    serport.write(bytearray([COMMANDBYTE_UPDATESCREEN]))

#TODO: improve tests
def drawPixelRgb(x,y,r,g,b):
    if (x>=0 and x<PIXEL_X and y>=0 and y<PIXEL_Y):
        serport.write(bytearray([COMMANDBYTE_DRAWPIXELRGB,x,y,r,g,b]))


def main():
    if TEST_MAX2719_DISPLAY:
        print("Testing the MAX2719 Secondary Display")
        spiPort = spi(port=0, device=0, gpio=noop())
        MAX2719device = max7219(spiPort, cascaded=MAX2719_DISPLAYS or 1, block_orientation=MAX2719_ORIENTATION,
                     rotate=MAX2719_ROTATION or 0, blocks_arranged_in_reverse_order=False)
        msg = "IO Testing"
        print(msg)
        show_message(MAX2719device, msg, fill="white", font=proportional(CP437_FONT))
        time.sleep(1)

    print("Starting Main Display Test")
    clearScreen()
    while True:
        for currentColor in range(5): # TODO implement a better version
            for x in range(PIXEL_X):
                for y in range(PIXEL_Y):
                    print("Setting Pixel @ (", str(x).zfill(2), "|", str(y).zfill(2),")")
                    if TEST_MAX2719_DISPLAY:
                        msg = str(x).zfill(2)+str(y).zfill(2)
                        #show_message(MAX2719device, msg, fill="white", font=proportional(CP437_FONT))
                        with canvas(MAX2719device) as draw:
                            text(draw, (0, 0), msg, fill="white", font=proportional(CP437_FONT))
                    if currentColor==0:
                        drawPixelRgb(x,y,255,   0,   0) #red
                    elif currentColor==1:
                        drawPixelRgb(x,y,   0, 255,   0) #green
                    elif currentColor==2:
                        drawPixelRgb(x,y,   255, 255,   0) #yellow                    
                    elif currentColor==3:
                        drawPixelRgb(x,y,     0, 255, 255) #cyan
                    elif currentColor==3:
                        drawPixelRgb(x,y,     255,   0, 255) #magenta
                    else:
                        drawPixelRgb(x,y,  0,   0, 255) #blue    
                    
                    updateScreen()
                    #time.sleep(0.1)

main()