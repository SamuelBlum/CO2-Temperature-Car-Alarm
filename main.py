import temp
import CO2
import alarm

temp = temp.TempSensor()
CO2 = CO2.CO2Sensor()

if temp > 100 and CO2 > 100:
        
    #set phone number and message and trigger car alarm
    access_key = ''
    secret_key = ''
    phone_number = ''
    message = ''

    # Create SNS client
    client = boto3.client(
        "sns",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1"
    )

    # Send sms message.
    client.publish(
        PhoneNumber=phone_number,
        Message=message
    )
