//www.elegoo.com
//2016.12.12

/************************
Exercise the motor using
the L293D chip
************************/

#define ENABLE 5
#define DIRA 3
#define DIRB 4

int i;
 
void setup() {
pinMode(11,OUTPUT);
    pinMode(10,OUTPUT);
pinMode(9,OUTPUT);
pinMode(8,OUTPUT);
pinMode(7,OUTPUT);
pinMode(6,OUTPUT);
pinMode(5,OUTPUT);
pinMode(4,OUTPUT);
digitalWrite(11,HIGH);
digitalWrite(10,HIGH);
digitalWrite(9,HIGH);
digitalWrite(8,HIGH);
digitalWrite(7,HIGH);
digitalWrite(6,HIGH);
digitalWrite(5,HIGH);
digitalWrite(4,HIGH);
  Serial.begin(9600);
  Serial.flush();
}

void loop() {
  
 
//---back and forth example
    //Serial.println("One way, then reverse");
    if (Serial.available()>0)
    {
        int state = Serial.parseInt();
        Serial.println(state);
        if(state == 11)
        {
          digitalWrite(11,LOW);
        }
        else if(state == 10)
        {
          digitalWrite(11,HIGH);
        }
        
    }
    //delay(100);
    
}
