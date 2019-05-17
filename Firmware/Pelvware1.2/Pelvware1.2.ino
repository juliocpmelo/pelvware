#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <WiFiUdp.h>
#include "FS.h"
#include <ESP8266FtpServer.h>

const int buttonPin = D0; // the number of the Button pin
//const int ledPin =  D4;    // the number of the POWER-ON LED pin

// Led red (D5) not working in this board.

const int ledV1Pin =  D6;    // the number of the POWER-ON LED pin
const int ledV2Pin =  D5;    // the number of the POWER-ON LED pin
const int ledV3Pin =  D7;    // the number of the POWER-ON LED pin

// Default parameters for test mode => 0.1 * sin(10x) + 0.1
double amplitude = 0.1;	// Default amplitude -0.1 to 0.1 // Shifted above zero generating 0 to 0.2 values.
double period = 10;     // Defaul Period 10.

boolean testMode = false;

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


// Configurations of wireless network and server (GUI).
String guiIP        = "";
String WIFIssid     = "";
String WIFIpassword = "";

/***
  ----------------------------------------------------------------------------------------------------------------------------
  Start of Functions used to configure the Wi-fi connection of the board.
  ----------------------------------------------------------------------------------------------------------------------------
***/

/** Function to connect on Wi-fi using the settings variables previous declared: WIFIssid and WIFIpassword.
 *  @return  true: Connect successful.
 *          false: Could not connect.
 */
boolean wifiConnect()
{
  WiFi.mode(WIFI_STA);

  /*Serial.print("SSID: ");
  Serial.println(WIFIssid);
  Serial.print("Pass: ");
  Serial.println(WIFIpassword);*/
  
  WiFi.begin( WIFIssid.c_str(), WIFIpassword.c_str() );

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

/** Function to get Wi-fi settings of the SPIFFS, and set the value on variables WIFIssid, WIFIpassword and guiIP.
 *  @return  true: Everything is ok in the file read.
 *          false: Can't open the file with settings or can't set on variables.
 */
boolean getWifiSettings()
{
  //Read File data
  File f = SPIFFS.open("/wifiSettings", "r");
  
  if (!f) {
    Serial.println("Failed to Open Wireless Settings !");
    return false;
  }
  else
  { 
    String settings = "";
    
    while(f.available()){
        settings += char(f.read());
    }

    f.close();  //Close file
    
    /*Serial.print("Wifi Settings: ");
    Serial.println(settings);*/
    
    return setWifiSettings(settings);
  }
}

/** Function to separe Wi-fi settings from a String and set the value on variables WIFIssid, WIFIpassword and guiIP.
 *  @return  true: Everything is ok in the String.
 *          false: The String contains few or many separators.
 */
boolean setWifiSettings(String settings)
{
  String temp = "";
  int countParts = 0;

  /*Serial.print("Settings: ");
  Serial.println(settings);*/

  for(int i = 0; i < settings.length() ; i++)
  {
    if( settings[i] == ';' || i == settings.length()-1 )
    {        
      /*Serial.print("i: ");
      Serial.print(i);
      Serial.print("Settings - 1: ");
      Serial.println(settings.length()-1);*/
      
      switch(countParts)
      {
        case 0:
          WIFIssid = temp;
        break;

        case 1:
           WIFIpassword = temp;
        break;

        case 2:
           temp += settings[i];
           guiIP = temp;
        break;
      } 

      temp = "";
      countParts++;
    }
    else
    {
      temp += settings[i];
    }
  }

  if( countParts != 3 )
    return false;
  else
    return true;
}

/** Function to save the values of setting wifi variables (WIFIssid, WIFIpassword and guiIP) in a file with the SPIFFS.
 *  @return  true: Everything is ok in the file write.
 *          false: The file can't be write.
 */
boolean saveWifiSettings()
{
  File f = SPIFFS.open("/wifiSettings", "w");
  
  if(!f) {
    Serial.println("Failed to Save Wireless Settings !");
    return false;
  }
  else{
    String wifiSettings = WIFIssid + ';' + WIFIpassword + ';' + guiIP;
    f.print(wifiSettings);
    
    f.close();
  }
  
  
  return true;
}

// TODO: Function to check testMode file from SPIFFS, and configure testMode if is enabled.
boolean checkTestMode()
{  
  return false;
}

// Function to set testMode state on file in SPIFFS.
boolean setTestMode(boolean value)
{
  boolean success = false;
  
  File f = SPIFFS.open("/testMode", "w");
  String name = f.name();
  
  if(!f) {
    Serial.println("File open failed");
    return false;
  }
  else{
    if(value){
      f.print('1');
    }
    else{
      f.print('0');
    }
    
    success = true;
    
    f.close();
  }
    
  testMode = value;
  
  
  return success;
}

boolean syncSerial()
{
    String data = waitAndGetData();
    
    if( data.equals("SerialSync") )
    {
      Serial.println("SyncOK");
      return true;
    }
    if( data.equals("EnableTestMode") )
    {
      
      if( setTestMode(true) )
        Serial.println("TestModeEnabled");
      else
        Serial.println("TestModeEnableError");
        
      return false;
    }
    if( data.equals("DisableTestMode") )
    {
      
      if( setTestMode(false) )
        Serial.println("TestModeDisabled");
      else
        Serial.println("TestModeDisableError");
      
      return false;
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

// Wait until get data from serial.
String waitAndGetData()
{
    String texto = "";
    
    while( (!Serial.available() > 0) );
    
    while( Serial.available() > 0)
    {
        texto += char(Serial.read());
        delay(10);
    }

    return texto;
}

// Try get data from serial, non blocking.
String tryGetData()
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
  String wifiSettings = "";
  int i21 = 0;

  while( (!Serial.available() > 0) );

  int contains = 0;

  delay(10);

  while( Serial.available() > 0)
  {
      char buffr = char( Serial.read() );
      wifiSettings += buffr;
      if(buffr == ';')
        contains++;
  }

  if( wifiSettings.equals("SerialSync") )
  {
    Serial.println("SyncOK");
    return false;
  }
  else if( contains == 2 )
  {
    if( setWifiSettings(wifiSettings) )
    {
      if( wifiConnect() )
      {
        saveWifiSettings();
        return true;
      }
      else
      {
        Serial.println("ConnectionError");  // Can be used with a diferent message.
        Serial.flush();
        return false;
      }
    }
    else
    {
      Serial.println("SSIDFormatError");  // Can be used with a diferent message.
      Serial.flush();
      return false;
    }
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
    delay(5);
    texto = tryGetData();
    if(texto == "ConfigurationStarted"){
      Serial.println("ConfigurationStarted");
      return true;
    }
  }
  
  Serial.println("Ops");

  return false;
}

/***
  ----------------------------------------------------------------------------------------------------------------------------
  End of Functions used to configure the Wi-fi connection of the board.
  ----------------------------------------------------------------------------------------------------------------------------
***/

void setup()
{
  //SPIFFS.format();
  
  Serial.begin(115200);

  udpRcv.begin(7500);

  pinMode(buttonPin, INPUT);
  //pinMode(ledPin, OUTPUT);
  pinMode(ledV1Pin, OUTPUT);
  pinMode(ledV2Pin, OUTPUT);
  pinMode(ledV3Pin, OUTPUT);
  //Serial.println("IP Address 1");
  //Serial.println(WiFi.localIP());

  // Initializing FTPServer and SPIFFS.
  if(SPIFFS.begin()){
    ftpSrv.begin("admin", "admin"); // Username and password.

    Serial.println("SPIIIFFFF");
    
    //Read File data
    File f = SPIFFS.open("/testMode", "r");
    
    if (!f) {
      Serial.println("file open failed");
    }
    else
    {
      char value = (char) f.read();

      if( value == '1' )
      {
        //Serial.println("ATTENTION: Test Mode Enabled");
        testMode = true;
      }
      else if(value == '0')
      {
        //Serial.println("ATTENTION: Test Mode Disabled");
      }
      else
      {
        //Serial.println("ATTENTION: Test Mode File Note Created");
      }
      
      f.close();  //Close file
    }
  }

  /*
  * Code used for turning the ESP into a WiFi Hotspot (Access Point).
  *
  */
  /*WiFi.softAP(ssid, password);

  IPAddress myIP = WiFi.softAPIP();*/

  if(pingSerial()){
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
  else
  {
    if( getWifiSettings() )
    {
      if( !wifiConnect() )
      {
        Serial.println("Deu Errado o wifiConnect...");
        ESP.restart();
      }
    }
    else
    {
        Serial.println("Deu Errado o getWifiSettings...");
        ESP.restart();
    }
  }

  //Serial.println(myIP);

  digitalWrite(ledV1Pin, LOW);
  digitalWrite(ledV2Pin, LOW);
  digitalWrite(ledV3Pin, LOW);
  //Serial.println("IP Address 1");
  //Serial.println(WiFi.localIP());
}

void readMyoware(){

  /*
   * Format File system before write new log file.
   */
  //SPIFFS.format();

  double analogIN = 0;
  const long interval = 5;           // interval of each reading (milliseconds)
  boolean first = true;
  int degree = 0;

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

      rtPause = true;

      delay(1000);

      break;
    }

    currentMillis = millis();

    if (currentMillis - previousMillis >= interval){
      
      if( testMode )
      {  
        double rad = degree * (PI/180);
        analogIN = ((amplitude * sin(rad*period)) + amplitude );
        
        if(degree < 360)
        {
          degree++;
        }
        else
        {
          degree = 0;
        }
        
      }
      else
      {
        analogIN = analogRead(A0);
      }

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
          String msg;
          
          if( testMode )
          {
            msg = String(analogIN);
          }
          else 
          {
            double conversion = (analogIN * ( (5.0/1023.0)*1000.0 ) ) / 10350.0 ;
            msg = String(conversion);
          }
          
          String milstr = String(elapsedMillis);
          
          udp.beginPacket(guiIP.c_str(), 5000);
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

    rtPause = false;
    
    delay(1000);

    readMyoware();
  }

  //digitalWrite(ledPin, LOW);
  digitalWrite(ledV1Pin, LOW);
  digitalWrite(ledV2Pin, LOW);
  digitalWrite(ledV3Pin, HIGH);

  ftpSrv.handleFTP();
}
