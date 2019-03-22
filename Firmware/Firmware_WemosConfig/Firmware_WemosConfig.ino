#include <ESP8266WiFi.h>
#include <WiFiClient.h> 

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
    
    while( (!Serial.available() > 0) );
    
    while( Serial.available() > 0)
    {
        texto += char(Serial.read());
    }

    return texto;
}

boolean getSSIDAndConnect()
{
  String texto = "";
  
  while( (!Serial.available() > 0) );

  boolean contains = false;
  
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

void setup()
{
  pinMode(BUILTIN_LED, OUTPUT);  // set onboard LED as output
  Serial.begin(115200);
  
  String texto = "";
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

void loop() 
{
  digitalWrite(BUILTIN_LED, HIGH);
  delay(500);
  digitalWrite(BUILTIN_LED, LOW);
  delay(500);
}
