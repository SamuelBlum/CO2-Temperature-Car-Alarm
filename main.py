import temp
import CO2
import alarm

temp = temp.TempSensor()
CO2 = CO2.CO2Sensor()

if temp > 100 and CO2 > 100:
    alarm.trigger()
