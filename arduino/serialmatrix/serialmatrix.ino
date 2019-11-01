// serialmatrix
// By M Oehler 
// https://hackaday.io/project/11064-raspberry-pi-retro-gaming-led-display
// Released under a "Simplified BSD" license
// ported to use Arduino Pro Micro by lowtexx
// Arduino Pro Micro has an USB Port --> the hardware Port is Serial1

// MO 04/05/2016 initial command set

#include <Adafruit_GFX.h>
#include <Adafruit_NeoMatrix.h>
#include <Adafruit_NeoPixel.h>

#define PIN 8

//TODO: move to Progmem
const uint32_t raspberry[] = { 
0x000000, 0x486748, 0x448833, 0x448833, 0x000000, 0x000000, 0x448833, 0x448833, 0x5a694b, 0x000000, 
0x000000, 0x518142, 0x55aa44, 0x559944, 0x447733, 0x448833, 0x559944, 0x55bb44, 0x5b884c, 0x000000, 
0x000000, 0x000000, 0x448833, 0x559944, 0x331122, 0x331122, 0x55aa44, 0x498b38, 0x000000, 0x000000, 
0x000000, 0x000000, 0x882244, 0x551122, 0xbb2255, 0xbb2244, 0x661122, 0x722443, 0x000000, 0x000000, 
0x000000, 0x000000, 0x661122, 0x661122, 0x661122, 0x771133, 0x771133, 0x882233, 0x000000, 0x000000, 
0x000000, 0x4f1622, 0x882233, 0xdd2255, 0x992233, 0xaa2244, 0xdd2255, 0x882233, 0x7c1b3b, 0x000000, 
0x000000, 0xa22040, 0x771133, 0xdd2255, 0x661122, 0x661122, 0xcc2255, 0x661122, 0xbb2244, 0x000000, 
0x000000, 0x551122, 0x551122, 0x5d1122, 0xdd2255, 0xcc2255, 0x5d1122, 0x771133, 0x5b1929, 0x000000, 
0x000000, 0x331122, 0xdd2255, 0x520000, 0xdd2255, 0xcc2255, 0x520000, 0xdd2255, 0x331122, 0x000000, 
0x000000, 0x000000, 0x833545, 0x441111, 0x661122, 0x661122, 0x551122, 0x8a414f, 0x000000, 0x000000, 
0x000000, 0x000000, 0x000000, 0x5d1122, 0x992345, 0x8b2839, 0x5d1122, 0x000000, 0x000000, 0x000000, 
0x000000, 0x000000, 0x000000, 0x000000, 0x5d1122, 0x5d1122, 0x000000, 0x000000, 0x000000, 0x000000};

// 20 x 10 pixel, zig-zag arranged stripes (10 columns, 20 rows)
Adafruit_NeoMatrix matrix = Adafruit_NeoMatrix(10, 20, PIN,
  NEO_MATRIX_BOTTOM    + NEO_MATRIX_LEFT +
  NEO_MATRIX_COLUMNS + NEO_MATRIX_ZIGZAG,
  NEO_GRB            + NEO_KHZ800);

// color palette
const uint16_t colors[] = {
  matrix.Color(0, 20, 0xE0), //blue
  matrix.Color(0, 0xB4, 0), //green
  matrix.Color(0xCC, 0, 0), //red
  matrix.Color(255, 215, 0), //yellow
  matrix.Color(0xAA, 0x6B, 0xE2), //cyan
  matrix.Color(0xDE, 0xB8, 0x87), //magenta
  matrix.Color(255,165,0), //orange
  matrix.Color(255, 255, 255), //white
  matrix.Color(0, 0, 0), //black
};
  
uint32_t pix;
uint16_t r,g,b;

int RX_LED_PIN = 17; // Pin of the RXLED on Arduino Pro
#define DEFAULT_BRIGHTNESS 30

void setup() {
  // pin configuration did not work! -- LED is ON
//  pinMode(RX_LED_PIN, OUTPUT);  // Set RX LED as an output
//  digitalWrite(RX_LED_PIN, HIGH);    // set the RX LED OFF

  //initialize the main display;
  // clear and disable fast to prevent bootup problems
  matrix.begin();
  matrix.setBrightness(DEFAULT_BRIGHTNESS);
  matrix.show();
  
  // draw bootscreen (raspberry)
  for (int c=0;c<10;c++)
  {
    for(int row=0;row<12;row++)
    {
      pix = raspberry[row*10+c];
      r = (uint16_t) (pix >>16);
      g = (uint16_t) ((pix >>8) & 0xFF);
      b = (uint16_t) (pix & 0xFF);
      matrix.drawPixel(c,4+row,matrix.Color(r,g,b));
    }
  } 
  matrix.show();
//for(int pixel=0; pixel <10; pixel++){
//  matrix.drawPixel(0,pixel,matrix.Color(0, 20, 0xE0));    
//} 
//matrix.show(); 
// serial interface is connected via USB --> Use Serial Monitor to see the output
  Serial.begin(250000);
  // TODO: will this work if no USB Cable is connected?
  //while(!Serial); 
  Serial.println("Matrix Display Driver - Start");
  
  //Set Baudrate to 250k
  Serial1.begin(250000);
  Serial1.setTimeout(60000);//TODO 1 minute timeout? ??
}

char buffer[200];


void loop() {
  //Serial.println("Cmd?");
  //Serial1.println("Arduino talking to Rasp. Hello?");
  Serial1.readBytes(buffer,1);
  
  switch(buffer[0])
  {
    // clear screen
    case 32:
      Serial.println("Clr");
      matrix.fillScreen(0);
      break;

    // update matrix
    case 30:
      Serial.println("Upd");
      matrix.show();
    break;

    // send 200 pixels with color out of palette to the matrix
    case 28:
      Serial1.readBytes(buffer,200);
      for (int c=0;c<10;c++)
      {
        for(int r=0;r<20;r++)
        {
          matrix.drawPixel(c,r,colors[buffer[c*10+r]]);
        }
      }     
    break;   

    // set a pixel (x,y) to color from palette
    case 26:
      Serial1.readBytes(buffer,3);
      matrix.drawPixel(buffer[0],buffer[1],colors[buffer[2]]);
    break;

    // set a pixel to rgb color (x,y,r,g,b)
    case 24:
      Serial.println("RGB");
      Serial1.readBytes(buffer,5);
      matrix.drawPixel(buffer[0],buffer[1],matrix.Color(buffer[2],buffer[3],buffer[4]));
      //matrix.show();
    break;   

    // set led brightness
    case 22:
      Serial1.readBytes(buffer,1);
      matrix.setBrightness(buffer[0]);
    break;  
    
  }
  
}
