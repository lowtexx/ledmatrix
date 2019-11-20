# WS2812 LED Matrix Gamecontrol (Tetris, Snake, Pong)
# by M Oehler
# https://hackaday.io/project/11064-raspberry-pi-retro-gaming-led-display
# ported from
# Tetromino (a Tetris clone)
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/pygame
# Released under a "Simplified BSD" license

import random, time, sys, socket, threading, queue, socketserver, os
from PIL import Image # tested with pillow-6.2.1

# If Pi = False the script runs in simulation mode using pygame lib
PI = True
import pygame
from pygame.locals import *
from random import randint # random numbers
import datetime
if PI:
    import serial
    from luma.led_matrix.device import max7219
    from luma.core.interface.serial import spi, noop
    from luma.core.render import canvas
    from luma.core.legacy.font import proportional, SINCLAIR_FONT, TINY_FONT, CP437_FONT
    from luma.core.legacy import show_message, text
    import asyncio
    from evdev import InputDevice, categorize, ecodes # PS4 inputs
    from select import select

# only modify this two values for size adaption!
PIXEL_X=10
PIXEL_Y=20


MAX2719_DISPLAYS=4 # number of cascaded displays
MAX2719_ORIENTATION=90 # Corrects block orientation when wired vertically choices=[0, 90, -90]
MAX2719_ROTATION=0 # Rotate display 0=0°, 1=90°, 2=180°, 3=270° choices=[0, 1, 2, 3]
#PORT_NAME = "/dev/ttyAMA0"
PORT_NAME = "/dev/ttyS0"
GAMEPAD_DEVICE = '/dev/input/event2' # PS4 Controler
#GAMEPAD_DEVICE = '/dev/input/event1' # PS3 Controller

SIZE= 20
FPS = 15
BOXSIZE = 20
WINDOWWIDTH = BOXSIZE * PIXEL_X
WINDOWHEIGHT = BOXSIZE * PIXEL_Y
BOARDWIDTH = PIXEL_X
BOARDHEIGHT = PIXEL_Y
BLANK = '.'
MOVESIDEWAYSFREQ = 0.15
MOVEDOWNFREQ = 0.15
FALLING_SPEED = 0.8

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

SCORES =(0,40,100,300,1200)

BORDERCOLOR = BLUE
BGCOLOR = BLACK
TEXTCOLOR = WHITE
TEXTSHADOWCOLOR = GRAY
COLORS      = (BLUE,GREEN,RED,YELLOW,CYAN,MAGENTA,ORANGE)
LIGHTCOLORS = (LIGHTBLUE, LIGHTGREEN, LIGHTRED, LIGHTYELLOW)
#assert len(COLORS) == len(LIGHTCOLORS) # each color must have light color

# constants defining the keys/buttons on the controller
BUTTON_LEFT=0 
BUTTON_RIGHT=1
BUTTON_UP=2
BUTTON_DOWN=3
BUTTON_BLUE=4
BUTTON_GREEN=5
BUTTON_RED=6
BUTTON_YELLOW=7

# Sony PS4 Controller Codes
# using evdev now; should be better to use pygame.joystick, but could not get this to work in the headless setup
PS4BTN_X=304
PS4BTN_CIRCLE=305
PS4BTN_TRIANGLE=307
PS4BTN_QUADRAT=308
PS4BTN_R2=313
PS4BTN_R1=311
PS4BTN_L2=312
PS4BTN_L1=310

#maps the evdev button code to the in-game button event name
# Ps4 Version --> maps an PS4 Button to the in-game event name
# using predfined constants from evdev
if PI:
    # controllerEventMapper = {
    #     BTN_SOUTH : BUTTON_DOWN,
    #     BTN_EAST : BUTTON_RIGHT,
    #     BTN_WEST : BUTTON_LEFT,
    #     BTN_NORTH: BUTTON_UP,
    #     BTN_TL : BUTTON_YELLOW,
    #     BTN_TL2 : BUTTON_RED,
    #     BTN_TR : BUTTON_GREEN,
    #     BTN_TR2 : BUTTON_BLUE
    # }
    controllerEventMapper = {
        PS4BTN_X : BUTTON_DOWN,
        PS4BTN_CIRCLE : BUTTON_RIGHT,
        PS4BTN_QUADRAT : BUTTON_LEFT,
        PS4BTN_TRIANGLE : BUTTON_UP,
        PS4BTN_L1 : BUTTON_YELLOW,
        PS4BTN_L2 : BUTTON_RED,
        PS4BTN_R1 : BUTTON_GREEN,
        PS4BTN_R2 : BUTTON_BLUE
    }
keyboardEventMapper = {
    pygame.K_DOWN : BUTTON_DOWN,
    pygame.K_RIGHT : BUTTON_RIGHT,
    pygame.K_LEFT : BUTTON_LEFT,
    pygame.K_UP: BUTTON_UP,
    pygame.K_4 : BUTTON_YELLOW,
    pygame.K_3 : BUTTON_RED,
    pygame.K_2 : BUTTON_GREEN,
    pygame.K_1 : BUTTON_BLUE
}

#constants for the communication with the external display driver (Arduino) - only 4 commands are currently used
#COMMANDBYTE_SETBRIGHTNESS = 22 # command to set the LED Brightness of the Main Display; Followed by 1 Byte: Brightness value
COMMANDBYTE_DRAWPIXELRGB = 24 # command to set a pixel to a RGB color; followed by 5 byte: X-pos, Y-pos, R-Value, G-Value, B-Value
COMMANDBYTE_DRAWPIXELCOLOR = 26 # command to set a pixel to a RGB color, selected from internal palet; followed by 3 byte: X-pos, Y-pos, Color-Index
#COMMANDBYTE_FULLSCREEN = 28 # command to set the full screen, followed by 200 bytes for each pixel, selected from internal pallet
COMMANDBYTE_UPDATESCREEN = 30 # command to update the screen
COMMANDBYTE_CLEARSCREEN  = 32 # command to clear the screen

# constants for the colors in the arduino matrix
COLORINDEX_BLUE = 0
COLORINDEX_GREEN = 1
COLORINDEX_RED = 2
COLORINDEX_YELLOW = 3
COLORINDEX_CYAN = 4
COLORINDEX_MAGENTA = 5
COLORINDEX_ORANGE = 6
COLORINDEX_WHITE = 7
COLORINDEX_BLACK = 8

TEMPLATEWIDTH = 5
TEMPLATEHEIGHT = 5


S_SHAPE_TEMPLATE = [['.....',
                     '.....',
                     '..OO.',
                     '.OO..',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..OO.',
                     '...O.',
                     '.....']]

Z_SHAPE_TEMPLATE = [['.....',
                     '.....',
                     '.OO..',
                     '..OO.',
                     '.....'],
                    ['.....',
                     '..O..',
                     '.OO..',
                     '.O...',
                     '.....']]

I_SHAPE_TEMPLATE = [['..O..',
                     '..O..',
                     '..O..',
                     '..O..',
                     '.....'],
                    ['.....',
                     '.....',
                     'OOOO.',
                     '.....',
                     '.....']]

O_SHAPE_TEMPLATE = [['.....',
                     '.....',
                     '.OO..',
                     '.OO..',
                     '.....']]

J_SHAPE_TEMPLATE = [['.....',
                     '.O...',
                     '.OOO.',
                     '.....',
                     '.....'],
                    ['.....',
                     '..OO.',
                     '..O..',
                     '..O..',
                     '.....'],
                    ['.....',
                     '.....',
                     '.OOO.',
                     '...O.',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..O..',
                     '.OO..',
                     '.....']]

L_SHAPE_TEMPLATE = [['.....',
                     '...O.',
                     '.OOO.',
                     '.....',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..O..',
                     '..OO.',
                     '.....'],
                    ['.....',
                     '.....',
                     '.OOO.',
                     '.O...',
                     '.....'],
                    ['.....',
                     '.OO..',
                     '..O..',
                     '..O..',
                     '.....']]

T_SHAPE_TEMPLATE = [['.....',
                     '..O..',
                     '.OOO.',
                     '.....',
                     '.....'],
                    ['.....',
                     '..O..',
                     '..OO.',
                     '..O..',
                     '.....'],
                    ['.....',
                     '.....',
                     '.OOO.',
                     '..O..',
                     '.....'],
                    ['.....',
                     '..O..',
                     '.OO..',
                     '..O..',
                     '.....']]

PIECES = {'S': S_SHAPE_TEMPLATE,
          'Z': Z_SHAPE_TEMPLATE,
          'I': I_SHAPE_TEMPLATE,
          'J': J_SHAPE_TEMPLATE,
          'L': L_SHAPE_TEMPLATE,
          'O': O_SHAPE_TEMPLATE,
          'T': T_SHAPE_TEMPLATE}

PIECES_ORDER = {'S': 0,'Z': 1,'I': 2,'J': 3,'L': 4,'O': 5,'T': 6}

# snake constants #
UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

HEAD = 0 # syntactic sugar: index of the worm's head

# font clock #
clock_font = [
  0x1F, 0x11, 0x1F,
  0x00, 0x00, 0x1F,
  0x1D, 0x15, 0x17,
  0x15, 0x15, 0x1F,
  0x07, 0x04, 0x1F,
  0x17, 0x15, 0x1D,
  0x1F, 0x15, 0x1D,
  0x01, 0x01, 0x1F,
  0x1F, 0x15, 0x1F,
  0x17, 0x15, 0x1F]

# serial port pi #

if PI:
    serport=serial.Serial(PORT_NAME,baudrate=250000,timeout=3.0)
    spiPort = spi(port=0, device=0, gpio=noop())
    MAX2719device = max7219(spiPort, cascaded=MAX2719_DISPLAYS, block_orientation=MAX2719_ORIENTATION,
                    rotate=MAX2719_ROTATION or 0, blocks_arranged_in_reverse_order=False)
    #creates object 'gamepad' to store the data
    gamepad = InputDevice(GAMEPAD_DEVICE)
    print(gamepad)
else:
    MAX2719device = 0

# key server for controller #

#TODO simply use pygame events?
QKEYDOWN=0
QKEYUP=1
myQueue = queue.Queue()
mask = bytearray([1,2,4,8,16,32,64,128])

class qEvent:
   def __init__(self, key, type):
        self.key = key
        self.type = type

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        oldstr=b'\x80'  #create event on connection start (0x80 != 0x00)
        while RUNNING:
            data = self.request.recv(1)
            #cur_thread = threading.current_thread()
            #response = bytes("{}: {}".format(cur_thread.name, data), 'ascii')
            if data:
                if data!=oldstr:
                    #print(str(time.time()) + ' -- ' + str(oldstr))
                    for i in range (0,8):
                        if (bytes(data[0]&mask[i])!=bytes(oldstr[0]&mask[i])) :
                            if (bytes(data[0]&mask[i])):
                                myQueue.put(qEvent(i,QKEYDOWN))
                            else:
                                myQueue.put(qEvent(i,QKEYUP))
                oldstr = data
                #print(data)
            #self.request.sendall(response)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    try:
        sock.sendall(bytes(message, 'ascii'))
        response = str(sock.recv(1024), 'ascii')
        print("Received: {}".format(response))
    finally:
        sock.close()


#checks for input of the gamepad, non blocking
def pollGamepadInput():
    r,w,x = select([gamepad], [], [],0)
    if r:
        for event in gamepad.read():
            if event.type == ecodes.EV_KEY:
                if event.value == 1: # button pressed
                    thisEventType = QKEYDOWN
                else:
                    thisEventType = QKEYUP
                # try to get the correct key mapping
                mappedEventCode = controllerEventMapper.get(event.code,-1)
                if mappedEventCode != -1: # only insert when button has a mapping
                    myQueue.put(qEvent(mappedEventCode,thisEventType)) 


def pollKeyboardInput():
    for event in pygame.event.get():
    #if event.type == pygame.QUIT:  # Usually wise to be able to close your program.
    #    raise SystemExit
        if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
            if event.type == pygame.KEYDOWN:
                thisEventType = QKEYDOWN
            else:
                thisEventType = QKEYUP
            mappedEventCode = keyboardEventMapper.get(event.key,-1)
            if mappedEventCode != -1: # only insert when button has a mapping
                myQueue.put(qEvent(mappedEventCode,thisEventType)) 

# main #
SCREEN_CLOCK = 0
SCREEN_TETRIS = 1
SCREEN_SNAKE = 2
SCREEN_PONG = 3

def main():

    global FPSCLOCK, DISPLAYSURF, BASICFONT, BIGFONT
    global RUNNING
    RUNNING=True

    if not PI:
        pygame.init()
        FPSCLOCK = pygame.time.Clock()
        DISPLAYSURF = pygame.display.set_mode((PIXEL_X*SIZE, PIXEL_Y*SIZE))
        BASICFONT = pygame.font.Font('freesansbold.ttf', 18)
        BIGFONT = pygame.font.Font('freesansbold.ttf', 100)
        pygame.display.set_caption('Pi Games')
    else:
        #MAX2719device.brightness(1) TODO needs fix
        MAX2719device.clear()
        #MAX2719device.show_message("Waiting for controller...", font=proportional(CP437_FONT),delay=0.015)

    # Port 0 means to select an arbitrary unused port

    HOST, PORT = '', 4711

    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    print("Server loop running in thread:", server_thread.name)
    currentScreen = SCREEN_TETRIS
    #nextScreen = -1
    clearScreen()
    drawClock(COLORINDEX_GREEN)
    clearScreen()
    # if PI:
    #     show_message(MAX2719device, "Let's play", fill="white", font=proportional(CP437_FONT),scroll_delay=0.03)
 
    while True:       
        updateStartScreen(currentScreen)
        while myQueue.empty():
            if PI:
                pollGamepadInput()
            else:
                pollKeyboardInput()
            time.sleep(.1)
            updateScreen()
            if not PI:
                checkForQuit()
            time.sleep(.1)
# use the down key as enter and right, left to toggle between start screens
        event = myQueue.get()
        if event.type == QKEYDOWN:
            if (event.key == BUTTON_LEFT): # goto previous start screen
                currentScreen-=1
                if(currentScreen==0):
                    currentScreen=3
            elif (event.key == BUTTON_RIGHT): # goto next start screen
                currentScreen+=1
                if(currentScreen==4):
                    currentScreen=1
            elif (event.key == BUTTON_DOWN): # start a game
                if(currentScreen==SCREEN_TETRIS):
                    runTetrisGame()
                    drawGameOverScreen()
                elif(currentScreen==SCREEN_PONG):
                    runPongGame()
                    drawGameOverScreen()
                elif(currentScreen==SCREEN_SNAKE):
                    runSnakeGame()
                    drawGameOverScreen()
            elif (event.key == BUTTON_UP): # goto Clock
                drawClock(COLORINDEX_GREEN)           
    terminate()

# gaming main routines #

def runPongGame():
    down = 0
    up = 1
    left = 0
    right = 1
    lowerbarx = PIXEL_X//2
    upperbarx = PIXEL_X//2
    score1 = 0
    score2 = 0
    ballx = PIXEL_X//2
    bally = PIXEL_Y//2
    directiony = down
    directionx = left
    movingRightUpper = False
    movingLeftUpper = False
    movingRightLower = False
    movingLeftLower = False
    restart=False
    lastLowerMoveSidewaysTime = time.time()
    lastUpperMoveSidewaysTime = time.time()

    while True: # main game loop for pong
        if PI:
            pollGamepadInput()
        else:
            pollKeyboardInput()
        while not myQueue.empty():
            event = myQueue.get()
            if event.type == QKEYDOWN:
                if (event.key == 0):
                    movingLeftLower = True
                    movingRightLower = False
                elif (event.key == 1):
                    movingLeftLower = False
                    movingRightLower = True
                elif (event.key == BUTTON_YELLOW):
                    movingLeftUpper = True
                    movingRightUpper = False
                elif (event.key == BUTTON_GREEN):
                    movingLeftUpper = False
                    movingRightUpper = True
                elif event.key == BUTTON_RED:
                     return
            if event.type == QKEYUP:
                if (event.key == 0):
                    movingLeftLower =False
                elif (event.key == 1):
                    movingRightLower = False
                elif (event.key == BUTTON_YELLOW):
                    movingLeftUpper = False
                elif (event.key == BUTTON_GREEN):
                    movingRightUpper = False

        if (movingLeftLower) and time.time() - lastLowerMoveSidewaysTime > MOVESIDEWAYSFREQ:
            if lowerbarx >1:
                lowerbarx-=1
            lastLowerMoveSidewaysTime = time.time()
        if (movingRightLower) and time.time() - lastLowerMoveSidewaysTime > MOVESIDEWAYSFREQ:
            if lowerbarx <PIXEL_X-2:
                lowerbarx+=1
            lastLowerMoveSidewaysTime = time.time()
        if (movingLeftUpper) and time.time() - lastUpperMoveSidewaysTime > MOVESIDEWAYSFREQ:
            if upperbarx >1:
                upperbarx-=1
            lastUpperMoveSidewaysTime = time.time()
        if (movingRightUpper) and time.time() - lastUpperMoveSidewaysTime > MOVESIDEWAYSFREQ:
            if upperbarx <PIXEL_X-2:
                upperbarx+=1
            lastUpperMoveSidewaysTime = time.time()

        if not PI:
                checkForQuit()

        if (directiony == up):
            if (bally>1):
                bally-=1
            else:
                if (abs(ballx-upperbarx)<2):
                    directiony = down
                    if (ballx==upperbarx+1):
                        if (directionx==left):
                            directionx=right
                    if (ballx==upperbarx-1):
                        if (directionx==right):
                            directionx=left
                elif ((ballx-upperbarx==2) and (directionx==left)):
                    directionx=right
                    directiony = down
                elif ((ballx-upperbarx==-2) and (directionx==right)):
                    directionx=left
                    directiony = down
                else:
                    bally-=1
                    score1+=1
                    restart = True
        else:
            if (bally<PIXEL_Y-2):
                bally+=1
            else:
                if (abs(ballx-lowerbarx)<2):
                    directiony = up
                    if (ballx==lowerbarx+1):
                        if (directionx==left):
                            directionx=right
                    if (ballx==lowerbarx-1):
                        if (directionx==right):
                            directionx=left
                elif ((ballx-lowerbarx==2) and (directionx==left)):
                    directionx=right
                    directiony = up
                elif ((ballx-lowerbarx==-2) and (directionx==right)):
                    directionx=left
                    directiony = up
                else:
                    bally+=1
                    score2+=1
                    restart = True

        if (directionx == left):
            if (ballx>0):
                ballx-=1
            else:
                directionx = right
                ballx+=1
                if(directiony == up):
                    if(bally>2):
                        bally-=1
                if(directiony == down):
                    if(bally<PIXEL_Y-2):
                        bally+=1
        else:
            if (ballx<PIXEL_X-1):
                ballx+=random.randint(1,2)
            else:
                directionx = left
                ballx-=random.randint(1,2)
                if(directiony == up):
                    if(bally>3):
                        bally-=random.randint(0,2)
                if(directiony == down):
                    if(bally<PIXEL_Y-3):
                        bally+=random.randint(0,2)

        clearScreen()
        drawBall(ballx,bally)
        drawBar(upperbarx,0)
        drawBar(lowerbarx,PIXEL_Y-1)
        #twoscoreText(score1,score2)
        updateScoreDisplayPong(score1,score2,MAX2719device)
        updateScreen()

        if (score1 == 9) or (score2 == 9):
            time.sleep(3)
            return

        if restart:
            time.sleep(1)
            ballx=PIXEL_X//2
            bally=PIXEL_Y//2
            if directiony==down:
                directiony = up
            else:
                directiony = down
            restart=False
        else:
            time.sleep(.1)

def runSnakeGame():
    # Set a random start point.
    startx = random.randint(2, BOARDWIDTH-2 )
    starty = random.randint(2, BOARDHEIGHT -2 )
    wormCoords = [{'x': startx,     'y': starty},
                  {'x': startx - 1, 'y': starty},
                  {'x': startx - 2, 'y': starty}]
    direction = RIGHT
    score = 0

    # Start the apple in a random place.
    apple = getRandomLocation()

    while True: # main game loop
        if PI:
            pollGamepadInput()
        else:
            pollKeyboardInput()
        if not myQueue.empty():
            event = myQueue.get()
            # take only one input per run
            while not myQueue.empty():
                myQueue.get()
            if event.type == QKEYDOWN:
                if (event.key == 0) and direction != RIGHT:
                    direction = LEFT
                elif (event.key == 1) and direction != LEFT:
                    direction = RIGHT
                elif (event.key == 2) and direction != DOWN:
                    direction = UP
                elif (event.key == 3) and direction != UP:
                    direction = DOWN
                elif (event.key == BUTTON_RED):
                     return

        # check if the worm has hit itself or the edge
        if wormCoords[HEAD]['x'] == -1 or wormCoords[HEAD]['x'] == BOARDWIDTH or wormCoords[HEAD]['y'] == -1 or wormCoords[HEAD]['y'] == BOARDHEIGHT:
            time.sleep(1.5)
            return # game over
        for wormBody in wormCoords[1:]:
            if wormBody['x'] == wormCoords[HEAD]['x'] and wormBody['y'] == wormCoords[HEAD]['y']:
                time.sleep(1.5)
                return # game over

        # check if worm has eaten an apple
        if wormCoords[HEAD]['x'] == apple['x'] and wormCoords[HEAD]['y'] == apple['y']:
            # don't remove worm's tail segment
            score += 1
            apple = getRandomLocation() # set a new apple somewhere
        else:
            del wormCoords[-1] # remove worm's tail segment

        # move the worm by adding a segment in the direction it is moving
        if direction == UP:
            if wormCoords[HEAD]['y'] == 0 :
                newHead = {'x': wormCoords[HEAD]['x'], 'y': BOARDHEIGHT-1}
            else:
                newHead = {'x': wormCoords[HEAD]['x'], 'y': wormCoords[HEAD]['y'] - 1}
        elif direction == DOWN:
            if wormCoords[HEAD]['y'] == BOARDHEIGHT-1 :
                newHead = {'x': wormCoords[HEAD]['x'], 'y': 0}
            else:
                newHead = {'x': wormCoords[HEAD]['x'], 'y': wormCoords[HEAD]['y'] + 1}
        elif direction == LEFT:
            if wormCoords[HEAD]['x'] == 0 :
                newHead = {'x': BOARDWIDTH -1, 'y': wormCoords[HEAD]['y'] }
            else:
                newHead = {'x': wormCoords[HEAD]['x'] - 1, 'y': wormCoords[HEAD]['y']}
        elif direction == RIGHT:
            if wormCoords[HEAD]['x'] == BOARDWIDTH-1:
                newHead = {'x': 0, 'y': wormCoords[HEAD]['y']}
            else:
                newHead = {'x': wormCoords[HEAD]['x'] + 1, 'y': wormCoords[HEAD]['y']}
        if not PI:
            checkForQuit()
        wormCoords.insert(0, newHead)
        clearScreen()
        drawWorm(wormCoords)
        drawApple(apple)
        updateScoreDisplaySnake(score,MAX2719device)
        #scoreText(score)
        updateScreen()
        time.sleep(.15)

def runTetrisGame():
    # setup variables for the start of the game
    if PI:
        #MAX2719device.brightness(1)
        #MAX2719device.flush()
        MAX2719device.clear()
    board = getBlankBoard()
    lastMoveDownTime = time.time()
    lastMoveSidewaysTime = time.time()
    lastFallTime = time.time()
    movingDown = False # note: there is no movingUp variable
    movingLeft = False
    movingRight = False
    score = 0
    oldscore = -1
    oldpiece = 10
    lines = 0
    level, fallFreq = calculateLevelAndFallFreq(lines)

    fallingPiece = getNewPiece()
    nextPiece = getNewPiece()

    # tetris listens to the keys
    # 0: Left --> move tile left
    # 1: Right --> move tile right
    # 2: Up --> rotate tile
    # 3: Down --> move tile down
    # 4: Button-Blue --> drop down
    # 5: BUTTON_GREEN --> rotates in other direction
    # 7: BUTTON_YELLOW --> ????
    while True: # game loop

        #if not myQueue.empty():
        #    print(myQueue.get().type)

        if fallingPiece == None:
            # No falling piece in play, so start a new piece at the top
            fallingPiece = nextPiece
            nextPiece = getNewPiece()
            lastFallTime = time.time() # reset lastFallTime

            if not isValidPosition(board, fallingPiece):
                time.sleep(2)
                return # can't fit a new piece on the board, so game over
        if not PI:
            checkForQuit()
        if PI:
            pollGamepadInput()
        else:
            pollKeyboardInput()
  

#ugly hack to get keyboard inputs directly without the simulation
#add the pygame key events to the local key event queue
#TODO this needs to be done globally
        # if not PI:
        #     for event in pygame.event.get():
        #     #if event.type == pygame.QUIT:  # Usually wise to be able to close your program.
        #     #    raise SystemExit
        #         if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
        #             if event.type == pygame.KEYDOWN:
        #                 thisEventType = QKEYDOWN
        #             else:
        #                 thisEventType = QKEYUP
        #             if event.key == pygame.K_UP:
        #                 myQueue.put(qEvent(BUTTON_UP,thisEventType)) 
        #             elif event.key == pygame.K_DOWN:
        #                 myQueue.put(qEvent(BUTTON_DOWN,thisEventType))
        #             elif event.key == pygame.K_LEFT:
        #                 myQueue.put(qEvent(BUTTON_LEFT,thisEventType))
        #             elif event.key == pygame.K_RIGHT:
        #                 myQueue.put(qEvent(BUTTON_RIGHT,thisEventType))
        #             elif event.key == pygame.K_1: # Maps #1 Key to Blue Button 
        #                 myQueue.put(qEvent(BUTTON_BLUE,thisEventType))
        #             elif event.key == pygame.K_2: # Maps #2 Key to Green Button 
        #                 myQueue.put(qEvent(BUTTON_GREEN,thisEventType))
        #             elif event.key == pygame.K_3: # Maps #3 Key to Red Button
        #                 myQueue.put(qEvent(BUTTON_RED,thisEventType))
        #             elif event.key == pygame.K_4: # Maps #4 Key to Yellow Button
        #                 myQueue.put(qEvent(BUTTON_YELLOW,thisEventType))

        while not myQueue.empty():
            event = myQueue.get()
            if event.type == QKEYUP:
                if (event.key == BUTTON_YELLOW):# TODO - what does this do?
                    lastFallTime = time.time()
                    lastMoveDownTime = time.time()
                    lastMoveSidewaysTime = time.time()
                elif (event.key == BUTTON_LEFT):
                    movingLeft = False
                elif (event.key == BUTTON_RIGHT):
                    movingRight = False
                elif (event.key == BUTTON_DOWN):
                    movingDown = False

            elif event.type == QKEYDOWN:
                # moving the piece sideways
                if (event.key == BUTTON_LEFT) and isValidPosition(board, fallingPiece, adjX=-1):
                    fallingPiece['x'] -= 1
                    movingLeft = True
                    movingRight = False
                    lastMoveSidewaysTime = time.time()
                elif (event.key == BUTTON_RIGHT) and isValidPosition(board, fallingPiece, adjX=1):
                    fallingPiece['x'] += 1
                    movingRight = True
                    movingLeft = False
                    lastMoveSidewaysTime = time.time()

                # rotating the piece (if there is room to rotate)
                elif (event.key == BUTTON_UP):
                    fallingPiece['rotation'] = (fallingPiece['rotation'] + 1) % len(PIECES[fallingPiece['shape']])
                    if not isValidPosition(board, fallingPiece):
                        fallingPiece['rotation'] = (fallingPiece['rotation'] - 1) % len(PIECES[fallingPiece['shape']])
                elif (event.key == BUTTON_GREEN): # rotate the other direction
                    fallingPiece['rotation'] = (fallingPiece['rotation'] - 1) % len(PIECES[fallingPiece['shape']])
                    if not isValidPosition(board, fallingPiece):
                        fallingPiece['rotation'] = (fallingPiece['rotation'] + 1) % len(PIECES[fallingPiece['shape']])

                # making the piece fall faster with the down key
                elif (event.key == BUTTON_DOWN):
                    movingDown = True
                    if isValidPosition(board, fallingPiece, adjY=1):
                        fallingPiece['y'] += 1
                    lastMoveDownTime = time.time()

                # move the current piece all the way down
                elif event.key == BUTTON_BLUE:
                    movingDown = False
                    movingLeft = False
                    movingRight = False
                    for i in range(1, BOARDHEIGHT):
                        if not isValidPosition(board, fallingPiece, adjY=i):
                            break
                    score+=i #TODO: more digits on numbercounter, more scores
                    fallingPiece['y'] += i - 1

        # handle moving the piece because of user input
        if (movingLeft or movingRight) and time.time() - lastMoveSidewaysTime > MOVESIDEWAYSFREQ:
            if movingLeft and isValidPosition(board, fallingPiece, adjX=-1):
                fallingPiece['x'] -= 1
            elif movingRight and isValidPosition(board, fallingPiece, adjX=1):
                fallingPiece['x'] += 1
            lastMoveSidewaysTime = time.time()

        if movingDown and time.time() - lastMoveDownTime > MOVEDOWNFREQ and isValidPosition(board, fallingPiece, adjY=1):
            fallingPiece['y'] += 1
            lastMoveDownTime = time.time()

        # let the piece fall if it is time to fall
        if time.time() - lastFallTime > fallFreq:
            # see if the piece has landed
            if not isValidPosition(board, fallingPiece, adjY=1):
                # falling piece has landed, set it on the board
                addToBoard(board, fallingPiece)
                remLine = removeCompleteLines(board)
                # count lines for level calculation
                lines += remLine
                # more lines, more points per line
                score += SCORES[remLine]*level
                level, fallFreq = calculateLevelAndFallFreq(lines)
                fallingPiece = None
            else:
                # piece did not land, just move the piece down
                fallingPiece['y'] += 1
                lastFallTime = time.time()

        # drawing everything on the screen
        clearScreen()
        drawBoard(board)
        #scoreText(score)
        if score>oldscore:
            updateScoreDisplayTetris(score,level,PIECES_ORDER.get(nextPiece['shape']),MAX2719device)
            oldscore = score
        if oldpiece!=PIECES_ORDER.get(nextPiece['shape']):
            updateScoreDisplayTetris(score,level,PIECES_ORDER.get(nextPiece['shape']),MAX2719device)
            oldpiece=PIECES_ORDER.get(nextPiece['shape'])
        #drawStatus(score, level)
        #drawNextPiece(nextPiece)
        if fallingPiece != None:
            drawPiece(fallingPiece)

        updateScreen()
        #FPSCLOCK.tick(FPS)
        time.sleep(.05)

def drawStartScreenTetris():
    drawPixel(8,15,COLORINDEX_RED)
    drawPixel(8,16,COLORINDEX_RED)
    drawPixel(8,17,COLORINDEX_RED)
    drawPixel(8,18,COLORINDEX_RED)

    drawPixel(6,18,COLORINDEX_BLUE)
    drawPixel(7,16,COLORINDEX_BLUE)
    drawPixel(7,17,COLORINDEX_BLUE)
    drawPixel(7,18,COLORINDEX_BLUE)

    drawPixel(4,17,COLORINDEX_YELLOW)
    drawPixel(3,18,COLORINDEX_YELLOW)
    drawPixel(4,18,COLORINDEX_YELLOW)
    drawPixel(5,18,COLORINDEX_YELLOW)

    drawPixel(2,18,COLORINDEX_GREEN)
    drawPixel(2,17,COLORINDEX_GREEN)
    drawPixel(3,17,COLORINDEX_GREEN)
    drawPixel(3,16,COLORINDEX_GREEN)




def drawStartScreenPong():
    drawPixel(4,8,COLORINDEX_GREEN)
    drawPixel(5,8,COLORINDEX_GREEN)
    drawPixel(6,8,COLORINDEX_GREEN)
    drawPixel(6,11,COLORINDEX_BLUE)
    drawPixel(5,13,COLORINDEX_GREEN)
    drawPixel(6,13,COLORINDEX_GREEN)
    drawPixel(7,13,COLORINDEX_GREEN)

def drawStartScreenSnake():
    drawPixel(5,3,COLORINDEX_RED)
    drawPixel(6,3,COLORINDEX_GREEN)
    drawPixel(7,3,COLORINDEX_GREEN)
    drawPixel(8,3,COLORINDEX_GREEN)
    drawPixel(8,2,COLORINDEX_GREEN)
    drawPixel(8,1,COLORINDEX_GREEN)

# display the game over screen, show the points at end of game
def drawGameOverScreen():
    while not myQueue.empty():
        myQueue.get()
    clearScreen()
    #E
    drawPixel(3,1,COLORINDEX_RED)
    drawPixel(4,1,COLORINDEX_RED)
    drawPixel(5,1,COLORINDEX_RED)
    drawPixel(6,1,COLORINDEX_RED)
    drawPixel(3,2,COLORINDEX_RED)
    drawPixel(3,3,COLORINDEX_RED)
    drawPixel(4,3,COLORINDEX_RED)
    drawPixel(5,3,COLORINDEX_RED)
    drawPixel(3,4,COLORINDEX_RED)
    drawPixel(3,5,COLORINDEX_RED)
    drawPixel(4,5,COLORINDEX_RED)
    drawPixel(5,5,COLORINDEX_RED)
    drawPixel(6,5,COLORINDEX_RED)

    #N
    drawPixel(3,7,COLORINDEX_RED)
    drawPixel(3,8,COLORINDEX_RED)
    drawPixel(3,9,COLORINDEX_RED)
    drawPixel(3,10,COLORINDEX_RED)
    drawPixel(3,11,COLORINDEX_RED)
    
    drawPixel(4,8,COLORINDEX_RED)
    drawPixel(5,9,COLORINDEX_RED)

    drawPixel(6,7,COLORINDEX_RED)
    drawPixel(6,8,COLORINDEX_RED)
    drawPixel(6,9,COLORINDEX_RED)
    drawPixel(6,10,COLORINDEX_RED)
    drawPixel(6,11,COLORINDEX_RED)

    #D
    drawPixel(3,13,COLORINDEX_RED)
    drawPixel(3,14,COLORINDEX_RED)
    drawPixel(3,15,COLORINDEX_RED)
    drawPixel(3,16,COLORINDEX_RED)
    drawPixel(3,17,COLORINDEX_RED)
    
    drawPixel(4,13,COLORINDEX_RED)
    drawPixel(5,13,COLORINDEX_RED)
    drawPixel(4,17,COLORINDEX_RED)
    drawPixel(5,17,COLORINDEX_RED)

    drawPixel(6,14,COLORINDEX_RED)
    drawPixel(6,15,COLORINDEX_RED)
    drawPixel(6,16,COLORINDEX_RED)
    updateScreen()
    time.sleep(0.5)
    
    while True:
        if PI:
            pollGamepadInput()
        else:
            checkForQuit()
            pollKeyboardInput()
        while not myQueue.empty():
            event = myQueue.get()
            if event.type == QKEYDOWN:
                if PI:
                    MAX2719device.clear()
                return



def updateStartScreen(currentScreen):
    clearScreen()
    if currentScreen==SCREEN_TETRIS:
        drawStartScreenTetris()
    elif currentScreen==SCREEN_PONG:
        drawStartScreenPong()
    elif currentScreen==SCREEN_SNAKE:
        drawStartScreenSnake()

def drawSymbols():
     #snbake symbol
    drawPixel(1,2,0)
    drawPixel(2,2,0)
    drawPixel(1,3,0)
    drawPixel(1,4,0)
    drawPixel(2,3,0)
    drawPixel(2,4,0)
    drawPixel(5,3,2)
    drawPixel(6,3,1)
    drawPixel(7,3,1)
    drawPixel(8,3,1)
    drawPixel(8,2,1)
    drawPixel(8,1,1)

    #pong symbol
    drawPixel(1,9,2)
    drawPixel(2,9,2)
    drawPixel(1,10,2)
    drawPixel(2,10,2)
    drawPixel(1,11,2)
    drawPixel(2,11,2)
    drawPixel(5,9,1)
    drawPixel(6,9,1)
    drawPixel(7,9,1)
    drawPixel(6,11,0)

    #tetris symbol
    drawPixel(1,16,3)
    drawPixel(2,16,3)
    drawPixel(1,17,3)
    drawPixel(1,18,3)
    drawPixel(2,17,3)
    drawPixel(2,18,3)
    drawPixel(7,16,0)
    drawPixel(6,16,0)
    drawPixel(6,17,0)
    drawPixel(6,18,0)

#TODO separate drawing and control flow
#draws a clock on the main screen with or without seconds
#color - 
def drawClock(color):
    if PI:
        MAX2719device.clear()
    lastExecutiontime = time.localtime(0)
    CLK_MODE_DEFAULT = 0 # 24h, no seconds
    CLK_MODE_SECONDS =1 # 24h, with seconds
    CLK_MODE_PARTY = 2 # Random Background
    CLK_MODE_PARTYTIME = 3 
    clockMode = CLK_MODE_DEFAULT

    while True:
        if PI:
            pollGamepadInput()
        else:
            pollKeyboardInput()
        while not myQueue.empty():
            event = myQueue.get()
            if event.type == QKEYDOWN:
                if event.key == BUTTON_RED: # toggle different clock modes
                    clockMode+=1
                    if clockMode==4:
                        clockMode=0
                else:
                    return
        if not PI:
            checkForQuit()

        now =  time.localtime()
        if (time.mktime(now)-time.mktime(lastExecutiontime)>0) :
            hour = now.tm_hour
            minute= now.tm_min
            second= now.tm_sec
            clearScreen()

            if(clockMode==CLK_MODE_PARTY or clockMode==CLK_MODE_PARTYTIME):
                #color=7
                for x in range(PIXEL_X):
                    for y in range(PIXEL_Y):
                        drawPixelRgb(x,y,randint(0,255),randint(0,255), randint(0,255))
                        time.sleep(0.001) #TODO saw some data loss without a delay

            if(clockMode==CLK_MODE_DEFAULT):
                drawnumber(int(hour/10),2,3,color)
                drawnumber(int(hour%10),6,3,color)
                drawnumber(int(minute/10),2,10,color)
                drawnumber(int(minute%10),6,10,color)
            elif(clockMode==CLK_MODE_SECONDS):
                drawnumber(int(hour/10),2,1,color)
                drawnumber(int(hour%10),6,1,color)
                drawnumber(int(minute/10),2,8,color)
                drawnumber(int(minute%10),6,8,color)
                drawnumber(int(second/10),2,15,color)
                drawnumber(int(second%10),6,15,color)
            elif(clockMode==CLK_MODE_PARTYTIME):
                drawnumber(int(hour/10),2,1,8)
                drawnumber(int(hour%10),6,1,8)
                drawnumber(int(minute/10),2,8,8)
                drawnumber(int(minute%10),6,8,8)
                drawnumber(int(second/10),2,15,8)
                drawnumber(int(second%10),6,15,8)

            updateScreen()
            time.sleep(.2)


def drawImage(filename):
    im = Image.open(filename)
    for row in range(0,BOARDHEIGHT):
        for col in range(0,BOARDWIDTH):
            r,g,b = im.getpixel((col,row))
            drawPixelRgb(col,row,r,g,b)
    updateScreen()

def drawHalfImage(filename,offset):
    im = Image.open(filename)
    if offset>10:
        offset = 10
    for row in range(0,10):
        for col in range(0,10):
            r,g,b = im.getpixel((col,row))
            drawPixelRgb(col,row+offset,r,g,b)

# drawing #

def clearScreen():
    if PI:
        serport.write(bytearray([COMMANDBYTE_CLEARSCREEN]))
    else:
        DISPLAYSURF.fill(BGCOLOR)

def updateScreen():
    if PI:
        serport.write(bytearray([COMMANDBYTE_UPDATESCREEN]))
    else:
        pygame.display.update()

def drawPixel(x,y,color):
    if color == BLANK:
        return
    if PI:
        if (x>=0 and y>=0 and color >=0):
            serport.write(bytearray([COMMANDBYTE_DRAWPIXELCOLOR,x,y,color]))
    else:
        pygame.draw.rect(DISPLAYSURF, COLORS[color], (x*SIZE+1, y*SIZE+1, SIZE-2, SIZE-2))

def drawPixelRgb(x,y,r,g,b):
    if PI:
        if (x>=0 and y>=0):
            serport.write(bytearray([COMMANDBYTE_DRAWPIXELRGB,x,y,r,g,b]))
    else:
        pygame.draw.rect(DISPLAYSURF, (r,g,b), (x*SIZE+1, y*SIZE+1, SIZE-2, SIZE-2))

def drawnumber(number,offsetx,offsety,color):
    for x in range(0,3):
        for y in range(0,5):
            if clock_font[3*number + x]&mask[y]:
                drawPixel(offsetx+x,offsety+y,color)

def makeTextObjs(text, font, color):
    surf = font.render(text, True, color)
    return surf, surf.get_rect()

def scrollText(text):
    if PI:
        show_message(MAX2719device, text, fill="white", font=proportional(CP437_FONT))
        #MAX2719device.show_message(text, font=proportional(CP437_FONT))
    else:
        titleSurf, titleRect = makeTextObjs(str(text), BASICFONT, TEXTCOLOR)
        titleRect.center = (int(WINDOWWIDTH / 2) - 3, int(WINDOWHEIGHT / 2) - 3)
        DISPLAYSURF.blit(titleSurf, titleRect)

# inserts a colon on the MAX7219 secondary display
# x - x coordinate on the display (0,0) is the left upper corner
# y - y coordinate on the display (0,0) is the left upper corner
# drawCanvas - the MAX7219 draw canvas
def scoreDisplayInsertColon(x,y,drawCanvas):
    drawCanvas.point((x,y+1), fill= "white")
    drawCanvas.point((x,y+3), fill= "white")

#TODO provide a pygame version of display
# inserts a single digit on the MAX7219 secondary display
# digit - digit to insert
# x - x coordinate on the display (0,0) is the left upper corner
# y - y coordinate on the display (0,0) is the left upper corner
# drawCancas - the MAX7219 draw canvas
def scoreDisplayInsertDigit(number,x,y,drawCanvas):
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

    for column in range(3): # 3 columns 
        for row in range(5): # 5 rows
            if((clock_font[3*number+column]>>row)&0x01==0x01):
                drawCanvas.point((x+column,y+row), fill= "white")

# inserts a the next tetris pice on the MAX7219 canvas
# nextPieceIndex - index of next piece to insert
# x - x coordinate on the display (0,0) is the left upper corner
# y - y coordinate on the display (0,0) is the left upper corner
# drawCanvas - the MAX7219 draw canvas
def scoreDisplayInsertNextPiece(nextPieceIndex,x,y,drawCanvas):
    # tetris clock #
    # 4x8 point font
    # each row is a symbol
    # each byte represents the vertical lines in binary
    theTetrisFont = [
        0x1E,0x1E,0x78,0x78, #Z
        0x78,0x78,0x1E,0x1E, #S
        0x00,0xFF,0xFF,0x00, #I
        0x7E,0x7E,0x06,0x06, #L
        0x06,0x06,0x7E,0x7E, #J
        0x3C,0x3C,0x3C,0x3C, #O
        0x7E,0x7E,0x18,0x18, #T
    ]   

    for column in range(4): # 4 columns 
        for row in range(8): # 5 rows
            if((theTetrisFont[4*nextPieceIndex+column]>>row)&0x01==0x01):
                drawCanvas.point((x+column,y+row), fill= "white")

# displays the score on the secondary screen for Snake
# score - score of player 
# dev - the MAX2719 device 
def updateScoreDisplaySnake(score,dev):
    _score=score
    if _score>9999: # not more than 4 digits for score
        _score = 9999
    if PI:
        with canvas(dev) as draw:
            for digit in range(4):
            # start with the smallest digit at the right side; 32 pixel display
                scoreDisplayInsertDigit(_score%10,29-4*digit,0,draw)
                _score //=10
    else:
        titleSurf, titleRect = makeTextObjs(str(_score), BASICFONT, TEXTCOLOR)
        titleRect.center = (int(WINDOWWIDTH / 2) - 3, int(WINDOWHEIGHT / 2) - 3)
        DISPLAYSURF.blit(titleSurf, titleRect)

# displays the score on the secondary screen for Tetris
# score - score of player 
# level - current level
# nextPiece - index of next piece
# dev - the MAX2719 device 
def updateScoreDisplayTetris(score,level,nextPiece,dev):
    _score=score
    if _score>999999: # not more than 6 digits for score
        _score = 999999
    
    # score as 6 digit value
    if PI:
        with canvas(dev) as draw:
            # two point per level? TODO what is the maximum level???
            for i in range(level):# insert level bar; 6 pixel offset to display next piece
                draw.point((2*i+6,7), fill= "white")
                draw.point((2*i+7,7), fill= "white")    
            for digit in range(6):
                # start with the smallest digit at the right side; 32 pixel display
                scoreDisplayInsertDigit(_score%10,29-4*digit,0,draw)
                _score //=10
            scoreDisplayInsertNextPiece(nextPiece,0,0,draw)

#displays the score on the secondary screen for pong
# score1 - score of player1 
# score2 - score of player2
# dev - the MAX2719 device 
def updateScoreDisplayPong(score1,score2,dev):
    _score1=score1
    if _score1>9: # not more than 1 digit for score
        _score1 = 9
    _score2=score2
    if _score2>9: # not more than 1 digit for score
        _score2 = 9
    if PI:
        with canvas(dev) as draw:
            scoreDisplayInsertDigit(_score2,29,0,draw)
            scoreDisplayInsertDigit(0,25,0,draw)
            scoreDisplayInsertColon(22,0,draw)
            scoreDisplayInsertDigit(_score1,17,0,draw)
            scoreDisplayInsertDigit(0,13,0,draw)
    else:
        titleSurf, titleRect = makeTextObjs(str(_score1)+':'+str(_score2), BASICFONT, TEXTCOLOR)
        titleRect.center = (int(WINDOWWIDTH / 2) - 3, int(WINDOWHEIGHT / 2) - 3)
        DISPLAYSURF.blit(titleSurf, titleRect)


# program flow #

def terminate():
    RUNNING = False
    if not PI:
        pygame.quit()
    sys.exit()

def checkForQuit():
    for event in pygame.event.get(QUIT): # get all the QUIT events
        terminate() # terminate if any QUIT events are present
    for event in pygame.event.get(KEYUP): # get all the KEYUP events
        if event.key == K_ESCAPE:
            terminate() # terminate if the KEYUP event was for the Esc key
        pygame.event.post(event) # put the other KEYUP event objects back

# tetris subroutines #

def calculateLevelAndFallFreq(lines):
    # Based on the score, return the level the player is on and
    # how many seconds pass until a falling piece falls one space.
    level = int(lines / 10) + 1
    # limit level to 10
    if level >10:
        level = 10
    fallFreq = FALLING_SPEED - (level * 0.05)
    if fallFreq <= 0.05:
        fallFreq = 0.05
    return level, fallFreq

def getNewPiece():
    # return a random new piece in a random rotation and color
    shape = random.choice(list(PIECES.keys()))
    newPiece = {'shape': shape,
                'rotation': random.randint(0, len(PIECES[shape]) - 1),
                'x': int(BOARDWIDTH / 2) - int(TEMPLATEWIDTH / 2),
                'y': -2, # start it above the board (i.e. less than 0)
                'color': PIECES_ORDER.get(shape)}
    return newPiece

def addToBoard(board, piece):
    # fill in the board based on piece's location, shape, and rotation
    for x in range(TEMPLATEWIDTH):
        for y in range(TEMPLATEHEIGHT):
            if PIECES[piece['shape']][piece['rotation']][y][x] != BLANK:
                board[x + piece['x']][y + piece['y']] = piece['color']

def isOnBoard(x, y):
    return x >= 0 and x < BOARDWIDTH and y < BOARDHEIGHT

def isValidPosition(board, piece, adjX=0, adjY=0):
    # Return True if the piece is within the board and not colliding
    for x in range(TEMPLATEWIDTH):
        for y in range(TEMPLATEHEIGHT):
            isAboveBoard = y + piece['y'] + adjY < 0
            if isAboveBoard or PIECES[piece['shape']][piece['rotation']][y][x] == BLANK:
                continue
            if not isOnBoard(x + piece['x'] + adjX, y + piece['y'] + adjY):
                return False
            if board[x + piece['x'] + adjX][y + piece['y'] + adjY] != BLANK:
                return False
    return True

def isCompleteLine(board, y):
    # Return True if the line filled with boxes with no gaps.
    for x in range(BOARDWIDTH):
        if board[x][y] == BLANK:
            return False
    return True

def removeCompleteLines(board):
    # Remove any completed lines on the board, move everything above them down, and return the number of complete lines.
    numLinesRemoved = 0
    y = BOARDHEIGHT - 1 # start y at the bottom of the board
    while y >= 0:
        if isCompleteLine(board, y):
            # Remove the line and pull boxes down by one line.
            for pullDownY in range(y, 0, -1):
                for x in range(BOARDWIDTH):
                    board[x][pullDownY] = board[x][pullDownY-1]
            # Set very top line to blank.
            for x in range(BOARDWIDTH):
                board[x][0] = BLANK
            numLinesRemoved += 1
            # Note on the next iteration of the loop, y is the same.
            # This is so that if the line that was pulled down is also
            # complete, it will be removed.
        else:
            y -= 1 # move on to check next row up
    return numLinesRemoved

def drawBoard(matrix):
    for i in range(0,BOARDWIDTH):
        for j in range(0,BOARDHEIGHT):
            drawPixel(i,j,matrix[i][j])

def getBlankBoard():
    # create and return a new blank board data structure
    board = []
    for i in range(BOARDWIDTH):
        board.append([BLANK] * BOARDHEIGHT)
    return board

def drawPiece(piece, pixelx=None, pixely=None):
    shapeToDraw = PIECES[piece['shape']][piece['rotation']]
    if pixelx == None and pixely == None:
        # if pixelx & pixely hasn't been specified, use the location stored in the piece data structure
        pixelx=piece['x']
        pixely=piece['y']

    # draw each of the boxes that make up the piece
    for x in range(TEMPLATEWIDTH):
        for y in range(TEMPLATEHEIGHT):
            if shapeToDraw[y][x] != BLANK:
                drawPixel( pixelx+ x , pixely+y,piece['color'])

# snake subroutines #

def getRandomLocation():
    return {'x': random.randint(0, BOARDWIDTH - 1), 'y': random.randint(0, BOARDHEIGHT - 1)}

def drawWorm(wormCoords):
    for coord in wormCoords:
        x = coord['x']
        y = coord['y']
        drawPixel(x,y,1)

def drawApple(coord):
    x = coord['x']
    y = coord['y']
    drawPixel(x,y,2)

# pong subroutines #

def drawBar(x,y):
    drawPixel(x-1,y,1)
    drawPixel(x,y,1)
    drawPixel(x+1,y,1)

def drawBall(x,y):
    drawPixel(x,y,0)

if __name__ == '__main__':
    main()
