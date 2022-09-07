#ifndef ReceiverState_hpp
#define ReceiverState_hpp
#include "PelvwareInfo.hpp"

class ReceiverState{
    private:
        bool m_connected;
        unsigned long m_timeLastMessage;
    
    public:
        ReceiverState(bool connected, unsigned long timeLastMessage){
            m_connected = connected;
            m_timeLastMessage = timeLastMessage;
        }

        void setConnected(bool connected){
            m_connected = connected;
        }
        bool isConnected(){
            return m_connected;
        }

        unsigned long getTimeLastMessage(){
            return m_timeLastMessage;
        }

        void setTimeLastMessage(unsigned long time){
            m_timeLastMessage = time;
        }

    /**
     * Tests the time since last message was received and return true if it is a TIMEOUT
     * Tests the difference between current time and time of last message received, 
     * if the difference is greater than TIMEOUT sets disconnected and return true, otherwhise return false
     * @param currenTime the current time im milliseconds
     * @return True if its a timetou, false otherwise
     **/
        bool isTimeout(unsigned long currentTime){
            if(currentTime - m_timeLastMessage >= PELVWARE_TIMEOUT){
                m_connected = false;
                return true;
            }
            return false;
        }
};


#endif