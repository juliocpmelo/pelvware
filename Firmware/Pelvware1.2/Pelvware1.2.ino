#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <WiFiUdp.h>
#include "FS.h"
#include <ESP8266FtpServer.h>

const int buttonPin =  D0; // the number of the Button pin
//const int ledPin =  D4;    // the number of the POWER-ON LED pin

const int ledV1Pin =  D5;    // the number of the POWER-ON LED pin
const int ledV2Pin =  D6;    // the number of the POWER-ON LED pin
const int ledV3Pin =  D7;    // the number of the POWER-ON LED pin


/***
  ----------------------------------------------------------------------------------------------------------------------------
  The Wi-Fi Configuration is going to be kept inside the flash of the device.
  ----------------------------------------------------------------------------------------------------------------------------
***/

//const char* ssid     = "cloudnet"; // SSID and Password are going to be stored at the SPIFFS
//const char* password = "Cloud123";

/*const char* ssid = "ESP_Pelv";
const char* password = "pelvware123";*/

FtpServer ftpSrv;
bool pelvMode = false; // Identifies if it's in the Real Time mode. (True = RT Mode ; False = FTP Mode);
bool rtPause = true;
WiFiUDP udp;
WiFiUDP udpRcv;
char rcvMsg[UDP_TX_PACKET_MAX_SIZE];
String convertedMsg;
char* guiIP = "10.0.0.1";

/***
  ----------------------------------------------------------------------------------------------------------------------------
  Start of Functions used to configure the Wi-fi connection of the board.
  ----------------------------------------------------------------------------------------------------------------------------
***/

boolean syncSerial()
{
    String data = waitAndGetData();

    if( data.equals("SerialSync") )
    {
      Serial.println("SyncOK");
      return true;
    }
    else
    {
      Serial.println("SyncError");
      Serial.flush();
      return false;
    }
}

String getSSIDS()
{
  int numberOfNetworks = WiFi.scanNetworks();
  String listWifi = "";

  for(int i = 0; i < numberOfNetworks; i++){

      if( i == numberOfNetworks-1 )
      {
        listWifi += WiFi.SSID(i);
      }
      else
        listWifi += WiFi.SSID(i) + ";";
  }

  return listWifi;
}

boolean getWifiList()
{
  String data = waitAndGetData();

  if( data.equals("GetWifiList") )
  {
      Serial.println( getSSIDS() );

      return true;
  }
  else if( data.equals("SerialSync") )
  {
    Serial.println("SyncOK");
    Serial.println( getSSIDS() );
    return true;
  }
  else
  {
    Serial.println("GetWifiListError");
    Serial.flush();
    return false;
  }
}

String waitAndGetData()
{
    String texto = "";
    int count = 0;

    delay(10);

    while( count < 3 ){
      if (!Serial.available() > 0)
      {
        delay(100);
        count++;
      }
      else{
        count = 3;
      }
    }

    while( Serial.available() > 0)
    {
        texto += char(Serial.read());
    }

    return texto;
}

boolean getSSIDAndConnect()
{
  String texto = "";
  int i21 = 0;

  while( (!Serial.available() > 0) );

  boolean contains = false;

  delay(10);

  while( Serial.available() > 0)
  {
      char buffr = char( Serial.read() );
      texto += buffr;
      if(buffr == ';')
        contains = true;
  }

  if( texto.equals("SerialSync") )
  {
    Serial.println("SyncOK");
    return false;
  }
  else if( contains )
  {
    boolean completeSSID = false;
    String ssid = "", password = "";

    for(int i = 0; i < texto.length(); i++)
    {
      if( !completeSSID )
      {
        if( texto[i] == ';' )
        {
          completeSSID = true;
        }
        else
          ssid += texto[i];
      }
      else
      {
          password += texto[i];
      }
    }

    WiFi.mode(WIFI_STA);
    WiFi.begin( ssid.c_str(), password.c_str() );

    int counterTimeOut = 0;

    while (WiFi.status() != WL_CONNECTED)
    {
      if( counterTimeOut == 50 )
      {
        Serial.println("ConectionTimeOut");
        Serial.flush();
        return false;
      }

      delay(500);
      counterTimeOut++;
    }

    Serial.println("Connected");
    Serial.println(WiFi.localIP());
    return true;
  }
  else
  {
    Serial.println("SSIDOrPasswordError");
    Serial.flush();
    return false;
  }
}

bool pingSerial(){
  String texto;
  for (int i = 0; i < 20; i++)
  {
    Serial.println("StartConfiguration");
    texto = waitAndGetData();
    if(texto = "ConfigurationStarted"){
      return true;
    }
  }
  return false;
}
/*
void connect(){
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}*/

/***
  ----------------------------------------------------------------------------------------------------------------------------
  End of Functions used to configure the Wi-fi connection of the board.
  ----------------------------------------------------------------------------------------------------------------------------
***/

void setup()
{
  Serial.begin(115200);

  udpRcv.begin(5050);

  pinMode(buttonPin, INPUT);
  //pinMode(ledPin, OUTPUT);
  pinMode(ledV1Pin, OUTPUT);
  pinMode(ledV2Pin, OUTPUT);
  pinMode(ledV3Pin, OUTPUT);

  /*
  * Code used for turning the ESP into a WiFi Hotspot (Access Point).
  *
  */
  /*WiFi.softAP(ssid, password);

  IPAddress myIP = WiFi.softAPIP();*/

  if(pingSerial){
    boolean SyncSerial = false;

    boolean configSuccess = false;

    while( !configSuccess )
    {
      while( !syncSerial() );

      boolean result = false;

      do
      {
        result = getWifiList();

        if( result )
        {
          if( getSSIDAndConnect() )
          {
            configSuccess = true;
          }
          else
            result = false;
        }

      }while( !result );
    }
  }
  else{

  }

  //Serial.println(myIP);

  // Initializing FTPServer and SPIFFS.
  if(SPIFFS.begin()){
    ftpSrv.begin("admin", "admin"); // Username and password.
  }

  digitalWrite(ledV1Pin, LOW);
  digitalWrite(ledV2Pin, LOW);
  digitalWrite(ledV3Pin, LOW);
}

void readMyoware(){

  /*
   * Format File system before write new log file.
   */
  //SPIFFS.format();

  int analogIN = 0;
  const long interval = 5;           // interval of each reading (milliseconds)
  boolean first = true;

  unsigned long currentMillis, previousMillis = 0, elapsedMillis = 0;

  //digitalWrite(ledPin, HIGH);

  /*
   *  Start read A0, signals of myoware.
   */

  Serial.println("Starting Read Myoware...");
  //delay(1000);

  /*Serial.println("Reading Analog IN, A0");
  Serial.println("Time;Value");*/

  while( true ){

    checkUDPMessage();

    if( digitalRead(buttonPin) == HIGH || rtPause == true ){

      while(digitalRead(buttonPin)){
        yield();
      }

      delay(1000);

      break;
    }

    currentMillis = millis();

    if (currentMillis - previousMillis >= interval){
      analogIN = analogRead(A0);

  /*
   * This part writes the EMG values that come from
   * the myoware and the time in millisecond on file system.
   */
      if(pelvMode==false){
        File f = SPIFFS.open("/teste", "w");
        //f.println("");
        f.close();
        f = SPIFFS.open("/teste", "a");
        String name = f.name();

        if(!f) {
          Serial.println("File open failed");
        }
        else{

          if( first ){
            first = false;
          }
          else
            f.println("");

          f.print(elapsedMillis);
          f.print(";");
          f.print(analogIN);
        }
        f.close();
      }
      else
      { if (WiFi.status() == WL_CONNECTED)
        {
          String msg = String(analogIN);
          String milstr = String(elapsedMillis);
          udp.beginPacket(guiIP, 5000);
          udp.println(milstr+";"+msg);
          udp.endPacket();
        }
      }
      //Serial.print( elapsedMillis );
      //Serial.print(";");
      /*Serial.print(analogIN);
      Serial.print(" -> ");
      Serial.println( (analogIN * ((5.0/1023.0)*1000.0))/10350.0 );*/

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


      /*
       *  save the last time you read A0
       */
      previousMillis = currentMillis;
      elapsedMillis += interval;
    }

    yield();
  }

  Serial.println("Stopping Read Myoware...");
  Serial.println();
  //delay(1000);

}

void checkUDPMessage(){
  int packetSize = udpRcv.parsePacket() > 0;
  convertedMsg = "";
  if(packetSize){
    udpRcv.read(rcvMsg, UDP_TX_PACKET_MAX_SIZE);
    Serial.println("Recebi:");
    Serial.println(rcvMsg);
    convertedMsg = String(rcvMsg);
    memset(rcvMsg, 0, UDP_TX_PACKET_MAX_SIZE);
  }
  if (convertedMsg == "startRT")
  {
    rtPause == false;
    Serial.println("RT Started");
  }
  else if(convertedMsg == "pauseRT")
  {
    rtPause = true;
    Serial.println("RT Paused");
  }
  else if(convertedMsg == "changeMode"){
    pelvMode = !pelvMode;
    Serial.println("Mode Changed");
  }
}

void loop()
{
  checkUDPMessage();

  if( digitalRead(buttonPin) == HIGH || rtPause == false)
  {
    while(digitalRead(buttonPin)){
      yield();
    }

    delay(1000);

    readMyoware();
  }

  //digitalWrite(ledPin, LOW);
  digitalWrite(ledV1Pin, LOW);
  digitalWrite(ledV2Pin, LOW);
  digitalWrite(ledV3Pin, HIGH);

  ftpSrv.handleFTP();
}
