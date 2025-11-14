#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "fonts/anorexia.h"
#include "fonts/cure.h"
#include "fonts/drift.h"
#include "fonts/edges.h"
#include "fonts/gelly.h"
#include "fonts/glisp.h"
#include "fonts/lime.h"
#include "fonts/mints-mild.h"
#include "fonts/mints-strong.h"
#include "fonts/nu.h"
#include "fonts/snap.h"

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

struct FontInfo {
  const GFXfont *font;
  const char *name;
};

FontInfo fonts[] = {
  {&anorexia, "anorexia"},
  {&cure, "cure"},
  {&drift, "drift"},
  {&edges, "edges"},
  {&gelly, "gelly"},
  {&glisp, "glisp"},
  {&lime, "lime"},
  {&mints_mild, "mints-mild"},
  {&mints_strong, "mints-strong"},
  {&nu, "nu"},
  {&snap, "snap"}
};

const int numFonts = sizeof(fonts) / sizeof(fonts[0]);
int currentFont = 0;

void setup() {
  Serial.begin(9600);

  // Initialize display
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }

  display.clearDisplay();
}

void loop() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0, 14);
  display.setFont(fonts[currentFont].font);
  display.println(fonts[currentFont].name);

  display.setCursor(0, 26);
  display.println(F("jackdaws love my big"));
  display.println(F("sphinx of quartz"));
  display.println(F("0123456789!@#$?"));
  display.display();

  currentFont = (currentFont + 1) % numFonts;
  delay(3000);
}
