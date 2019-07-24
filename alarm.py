#need to add code to trigger car alarm... or send car owner an alert through SNS

def trigger():
    
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

def main():
    
    access_key = ''
    secret_key = ''
    phone_number = ''
    message = ''
    trigger(access_key, secret_key, phone_number, message)

if __name__ == '__main__' :

    main()
