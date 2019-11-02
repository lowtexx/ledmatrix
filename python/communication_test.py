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
import sys
from random import randint
if TEST_MAX2719_DISPLAY:
    from luma.led_matrix.device import max7219
    from luma.core.interface.serial import spi, noop
    from luma.core.legacy import show_message, text
    from luma.core.render import canvas
    from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT
#    from luma.core.legacy import text, show_message
#    from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT

# only modify this two values for size adaption!
PIXEL_X=10
PIXEL_Y=20

#PORT_NAME = "/dev/ttyAMA0"
PORT_NAME = "/dev/ttyS0"

#constants for the communication with the external display driver (Arduino)
COMMANDBYTE_SETBRIGHTNESS = 22 # command to set the LED Brightness of the Main Display; Followed by 1 Byte: Brightness value
COMMANDBYTE_DRAWPIXELRGB = 24 # command to set a pixel to a RGB color; followed by 5 byte: X-pos, Y-pos, R-Value, G-Value, B-Value
COMMANDBYTE_DRAWPIXELCOLOR = 26 # command to set a pixel to a RGB color, selected from internal palet; followed by 3 byte: X-pos, Y-pos, Color-Index
COMMANDBYTE_FULLSCREEN = 28 # command to set the full screen, followed by 200 bytes for each pixel, selected from internal pallet
COMMANDBYTE_UPDATESCREEN = 30 # command to update the screen
COMMANDBYTE_CLEARSCREEN  = 32 # command to clear the screen



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
        for x in range(64):
            for y in range(8):
                with canvas(MAX2719device) as draw:
                    draw.point((x,y), fill= "white")
                    time.sleep(0.01)
        
        msg="012345"
        with canvas(MAX2719device) as draw: # show_text scrolls -- this is much faster
            text(draw, (0, 0), msg, fill="white", font=proportional(TINY_FONT))
        time.sleep(1)
        for number in range(10):
            scoreDisplayDrawDigit(number,number*2,0,MAX2719device)
            time.sleep(0.8)
        while True:
            time.sleep(0.1)
    sys.exit()#bug only for now
    print("Starting Main Display Test")
    clearScreen()
    while True:
        for i in range(50):
            for x in range(PIXEL_X):
                for y in range(PIXEL_Y):
                    drawPixelRgb(x,y,randint(0,255),randint(0,255), randint(0,255))
                    time.sleep(0.001) #TODO saw some data loss without a delay
            updateScreen()
            time.sleep(0.5)        
        time.sleep(1)
        for currentColor in range(5): # TODO implement a better version
            for x in range(PIXEL_X):
                for y in range(PIXEL_Y):
                    print("Setting Pixel @ (", str(x).zfill(2), "|", str(y).zfill(2),")")
                    if TEST_MAX2719_DISPLAY:
                        msg = str(x).zfill(2)+str(y).zfill(2)
                        #show_message(MAX2719device, msg, fill="white", font=proportional(CP437_FONT))
                        with canvas(MAX2719device) as draw: # show_text scrolls -- this is much faster
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

# draws a single digit on the MAX7219 secondary display
# number - number to draw
# x - x coordinate on the display (0,0) is the left upper corner
# y - y coordinate on the display (0,0) is the left upper corner
# dev - the MAX7219 device
def scoreDisplayDrawDigit(number,x,y,dev):
    # font clock #
    # 3x5 point font
    # each row is a digit
    # each byte represents the vertical lines in binary
    clock_font = [
        0x1F, 0x11, 0x1F, #0
        0x00, 0x00, 0x1F, #1
        0x1D, 0x15, 0x17, #2
        0x15, 0x15, 0x1F, #3
        0x07, 0x04, 0x1F, #4
        0x17, 0x15, 0x1D, #5
        0x1F, 0x15, 0x1D, #6
        0x01, 0x01, 0x1F, #7
        0x1F, 0x15, 0x1F, #8
        0x17, 0x15, 0x1F] #9

    with canvas(dev) as draw:
        for column in range(3): # 3 columns 
            for row in range(5): # 5 rows
                if((clock_font[3*number+column]>>row)&0x01==0x01):
                    draw.point((x+column,y+row), fill= "white")


main()