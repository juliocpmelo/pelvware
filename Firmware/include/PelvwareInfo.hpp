#ifndef PelvwareInfo_hpp
#define PelvwareInfo_hpp

#define PELVWARE_VERSION "Pelvware-1.0.0"
#define PELVWARE_VERSION_NUM 100

/*Timeout used to trigger disconnection when PELVWARE_TIMOUT milliseconds have passed since last message received*/
#define PELVWARE_TIMEOUT 1000

/*sample interval in millisecs*/
#define SAMPLE_INTERVAL 5 

/*mac addresses of the sender and receiver*/
static uint8_t receiverAddress[] = {0xCC,0x50,0xE3,0x0B,0xED,0x9F}; //receiver address
static uint8_t pelvwareAddress[] = {0xEC,0xFA,0xBC,0x0E,0xA8,0xBF}; //device address

#endif