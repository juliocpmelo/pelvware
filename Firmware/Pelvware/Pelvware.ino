#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <WiFiUdp.h>
#include "FS.h"
#include "PelvwareState.hpp"
#include "Messages.hpp"
#include "PelvwareInfo.hpp"
#include <espnow.h>

const int buttonPin = D0; // the number of the Button pin
//const int ledPin =  D4;    // the number of the POWER-ON LED pin

const int ledV1Pin =  D6;    // the number of the POWER-ON LED pin
const int ledV2Pin =  D5;    // the number of the POWER-ON LED pin
const int ledV3Pin =  D7;    // the number of the POWER-ON LED pin

/*sensor state*/
static PelvwareState pelvwareState = PelvwareState::SENSOR_MODE;

// TODO: Function to check testMode file from SPIFFS, and configure testMode if is enabled.
boolean checkTestMode()
{  
  return false;
}

// Callback when data is sent
void OnDataSent(uint8_t *mac_addr, uint8_t sendStatus) {
  if (sendStatus != 0){
    Serial.println("Cant send messages");
  }
}


void processCmd(Command cmd){
  
  switch (cmd.type)
  {
    case CommandType::GET_VERSION:
    {
      auto msg = PelvwareMessages::getVersionResponse();
      esp_now_send(receiverAddress, (uint8_t *) &msg, sizeof(msg));
      break;
    }
    case CommandType::TOOGLE_TEST_MODE:
    {
      if(pelvwareState == PelvwareState::SENSOR_MODE)
        pelvwareState = PelvwareState::TEST_MODE;
      else
        pelvwareState = PelvwareState::SENSOR_MODE;
      break;
    }
    default:
      //should not reach here
      break;
  }
}

// Callback when data is received
void OnDataRecv(uint8_t * mac, uint8_t *incomingData, uint8_t len) {
  PelvwareData data;
  memcpy(&data, incomingData, sizeof(PelvwareData));
  switch (data.type)
  {
    case MessageType::HEART_BEAT:
      /*do nothing for now*/
      break;
    case MessageType::COMMAND:
      processCmd(data.content.cmd);
      break;
    default:
      break;
  }
}

void setup()
{

  Serial.begin(115200);

  pinMode(buttonPin, INPUT);
  //pinMode(ledPin, OUTPUT);
  pinMode(ledV1Pin, OUTPUT);
  pinMode(ledV2Pin, OUTPUT);
  pinMode(ledV3Pin, OUTPUT);

  Serial.println();
  Serial.print("Endereco MAC: ");
  Serial.println(WiFi.macAddress());

  WiFi.mode(WIFI_STA);
  // Set ESP-NOW Role
  esp_now_set_self_role(ESP_NOW_ROLE_COMBO);

  // Once ESPNow is successfully Init, we will register for Send CB to
  // get the status of Trasnmitted packet
  esp_now_register_send_cb(OnDataSent);

  // Register peer
  esp_now_add_peer(receiverAddress, ESP_NOW_ROLE_COMBO, 1, NULL, 0);
  
  // Register for a callback function that will be called when data is received
  esp_now_register_recv_cb(OnDataRecv);

  Serial.println("Starting Pelvware...");

  digitalWrite(ledV1Pin, LOW);
  digitalWrite(ledV2Pin, LOW);
  digitalWrite(ledV3Pin, LOW);
}


void readMyoware(){

  static unsigned long lastTimeSent = 0; //last time a measurement was made
  static int degree = 0; //used in test mode to generate a sine wave
  unsigned long elapsedMillis = millis();


  if (elapsedMillis - lastTimeSent >= SAMPLE_INTERVAL){
    
    /*test mode generates sinoidal*/
    double conversion;

    if( pelvwareState == PelvwareState::TEST_MODE )
    { 
      const double amplitude = 0.1;	// Default amplitude -0.1 to 0.1 // Shifted above zero generating 0 to 0.2 values.
      const double period = 10;     // Defaul Period 10.

      double rad = degree * (PI/180);
      double analogIN = ((amplitude * sin(rad*period)) + amplitude );
      
      if(degree < 360)
      {
        degree++;
      }
      else
      {
        degree = 0;
      }
      conversion = analogIN;
    }
    else
    {
      double analogIN = analogRead(A0);
      conversion = (analogIN * ( (5.0/1023.0)*1000.0 ) ) / 10350.0 ;
    }
      
    auto pelvwareData = PelvwareMessages::buildSensorMessage(conversion, elapsedMillis);

    auto res = esp_now_send(receiverAddress, (uint8_t *) &pelvwareData, sizeof(pelvwareData));

    Serial.printf("Esp now return %d\n", res);

    if( pelvwareState == PelvwareState::TEST_MODE ){ //in test mode use leds to test the sensor
      double analogIN = analogRead(A0);
      conversion = (analogIN * ( (5.0/1023.0)*1000.0 ) ) / 10350.0 ;
      if( analogIN > 300 )
      {
        digitalWrite(ledV1Pin, HIGH);
        digitalWrite(ledV2Pin, HIGH);
        digitalWrite(ledV3Pin, HIGH);
      }
      else if(analogIN > 100)
      {
        digitalWrite(ledV1Pin, HIGH);
        digitalWrite(ledV2Pin, HIGH);
        digitalWrite(ledV3Pin, LOW);
      }
      else
      {
        digitalWrite(ledV1Pin, HIGH);
        digitalWrite(ledV2Pin, LOW);
        digitalWrite(ledV3Pin, LOW);
      }
    }
    lastTimeSent = elapsedMillis;
  }
}

void checkSerial(){
  /*some debug, or command mode here?*/
}


void loop()
{
  
  static unsigned long lastBlink = 0;
  static int heartBeatLedState = HIGH;

  checkSerial();
  readMyoware();

  if(millis() - lastBlink >= 1000){
    heartBeatLedState = (heartBeatLedState == HIGH) ? LOW : HIGH;
    lastBlink = millis();
  }

  digitalWrite(ledV3Pin, heartBeatLedState);
}
