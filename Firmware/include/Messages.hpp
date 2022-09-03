#ifndef Messages_hpp
#define Messages_hpp

#include "PelvwareInfo.hpp"

/*messages exchanged between peers*/
enum MessageType{
  HEART_BEAT,
  SENSOR_DATA,
  COMMAND,
  COMMAND_RESPONSE
};

enum CommandType{
  GET_VERSION,
  TOOGLE_TEST_MODE
};

struct Command{
  CommandType type;
  int data;
};

struct SensorData{
  double reading;
  unsigned long timestamp;
};

struct PelvwareData{
  MessageType type;
  union {
    Command cmd;
    SensorData sensorData;  
  } content;
  
};

class PelvwareMessages {
  public:
    static PelvwareData heartBeatMessage(){
      auto retVal = PelvwareData();
      retVal.type = HEART_BEAT;
      return retVal;
    }
    static PelvwareData toogleTestModeMessage(){
      auto retVal = PelvwareData();
      retVal.type = COMMAND;
      retVal.content.cmd.type = TOOGLE_TEST_MODE;
      return retVal;
    }
    static PelvwareData getVersionMessage(){
      auto retVal = PelvwareData();
      retVal.type = COMMAND;
      retVal.content.cmd.type = GET_VERSION;
      return retVal;
    }
    static PelvwareData getVersionResponse(){
      auto retVal = PelvwareData();
      retVal.type = COMMAND_RESPONSE;
      retVal.content.cmd.type = GET_VERSION;
      retVal.content.cmd.data = PELVWARE_VERSION_NUM;
      return retVal;
    }
    static PelvwareData buildSensorMessage(double reading, unsigned long timestamp){
      auto retVal = PelvwareData();
      retVal.type = SENSOR_DATA;
      retVal.content.sensorData.reading = reading;
      retVal.content.sensorData.timestamp = timestamp;
      return retVal;
    }
};

#endif