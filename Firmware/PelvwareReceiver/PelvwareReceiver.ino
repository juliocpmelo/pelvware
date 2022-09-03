#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <WiFiUdp.h>
#include "FS.h"
#include <espnow.h>
#include <ESP8266FtpServer.h>
#include "Messages.hpp"
#include "ReceiverState.hpp"

#define PELVWARE_VERSION "Pelvware-1.0.0"

/*heartbeat each 2 secs*/
#define PELVWARE_HEARTBEAT_TIME 2000

const int buttonPin = D0; // the number of the Button pin
//const int ledPin =  D4;    // the number of the POWER-ON LED pin

// Led red (D5) not working in this board.

const int ledV1Pin =  D6;    // the number of the POWER-ON LED pin
const int ledV2Pin =  D5;    // the number of the POWER-ON LED pin
const int ledV3Pin =  D7;    // the number of the POWER-ON LED pin

const int receiverBuiltinLed = 2; //inverted logic

// Default parameters for test mode => 0.1 * sin(10x) + 0.1
double amplitude = 0.1;	// Default amplitude -0.1 to 0.1 // Shifted above zero generating 0 to 0.2 values.
double period = 10;     // Defaul Period 10.

/*stores the state representation of the receiver*/
ReceiverState state = ReceiverState::DISCONNECTED;

void OnDataSent(uint8_t *mac_addr, uint8_t sendStatus) {
  if (!sendStatus == 0){
    state = ReceiverState::DISCONNECTED;
  }
}

// Callback when data is received
void OnDataRecv(uint8_t * mac, uint8_t *incomingData, uint8_t len) {
  PelvwareData pelvwareData;
  static unsigned long timeLastMessage = 0;
  memcpy(&pelvwareData, incomingData, sizeof(PelvwareData));
  switch(pelvwareData.type){
    case MessageType::SENSOR_DATA:
    {
      state = ReceiverState::CONNECTED;
      auto last = millis();
      auto timeDiff = last - timeLastMessage; //time between last message received and the current
      Serial.printf("d %lf %lu %lu\n",pelvwareData.content.sensorData.reading, pelvwareData.content.sensorData.timestamp, timeDiff);
      timeLastMessage = last;
      break;
    }
    default:
      Serial.printf("Unsupported data type received\n");
      break;
  }
}

void setup(){

  Serial.begin(115200);

  pinMode(2, OUTPUT);
  pinMode(14, OUTPUT);
  
  Serial.println();
  Serial.print("Endereco MAC: ");
  Serial.println(WiFi.macAddress());

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != 0) {
    Serial.println("Erro ao inicializar o ESP-NOW");
    return;
  }
  // Set ESP-NOW Role
  esp_now_set_self_role(ESP_NOW_ROLE_COMBO);

  // Once ESPNow is successfully Init, we will register for Send CB to
  // get the status of Trasnmitted packet
  esp_now_register_send_cb(OnDataSent);

  // Register peer
  esp_now_add_peer(pelvwareAddress, ESP_NOW_ROLE_COMBO, 1, NULL, 0);
  
  // Register for a callback function that will be called when data is received
  esp_now_register_recv_cb(OnDataRecv);
}

boolean sendMessage(PelvwareData &msg){
  if (esp_now_send(pelvwareAddress, (uint8_t *)&msg, sizeof(msg)) != 0){
    state = ReceiverState::DISCONNECTED;
    Serial.println("Cant send hb message");
    return false;
  }
  return true;
}

#define CMD_DELIM '\n'
/**
 * Receives dada throgh serial and outpts propper results
 * Supported commands are:
 *  st -> prints to serial current status
 *  ve -> prints to serial current version (value of PELVWARE_VERSION)
 * For debug purposes ignored commands are also printed
*/
void processSerialCommands(){
  if(Serial.available()){
    String cmd = Serial.readStringUntil(CMD_DELIM);
    if(cmd == "cn"){
    }
    else if(cmd == "st"){ /*status command*/
      Serial.printf("d %d", state == ReceiverState::CONNECTED);
    }
    else if(cmd == "ve"){ /*version command*/
      Serial.printf("d %s\n", PELVWARE_VERSION);
    }
    else if(cmd == "tm"){ /*test mode toogle*/
      auto data = PelvwareMessages::toogleTestModeMessage();
      if(!sendMessage(data)){
        Serial.printf("d FAIL\n");
      }
    }
    else{
      Serial.printf("d Command %s ignored\n",cmd.c_str());
    }
  }
}

void processPelvwareHeartbeat(){
  static unsigned long lastHeartbeat = 0;
  auto elapsedTime = millis() - lastHeartbeat;
  if(elapsedTime > PELVWARE_HEARTBEAT_TIME){ //sends heartbeat to check if it is connected
    lastHeartbeat = millis();
    auto data = PelvwareMessages::heartBeatMessage();
    if (!sendMessage(data))
      state = ReceiverState::DISCONNECTED;
  }
}

void loop(){

  static unsigned long lastBlink = 0;
  static int heartBeatLedState = HIGH;

  processSerialCommands();
  processPelvwareHeartbeat();

  if(state == ReceiverState::CONNECTED){
    if(millis() - lastBlink >= 1000){
      heartBeatLedState = (heartBeatLedState == HIGH) ? LOW : HIGH;
      lastBlink = millis();
    }
  }
  else{ //not connected will stop blinking / turn off
    heartBeatLedState = HIGH; //D1 mini has inverted logic on builtin led, so to turn it off we must set to HIGH ;x
  }
  //Serial.printf("State %d %d\n", state == ReceiverState::CONNECTED, heartBeatLedState);
  digitalWrite(receiverBuiltinLed, heartBeatLedState);
}
