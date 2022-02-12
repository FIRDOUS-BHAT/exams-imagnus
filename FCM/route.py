# Send to single device.
from pyfcm import FCMNotification


api_key = "REDACTED_FCM_SERVER_KEY"
push_service = FCMNotification(api_key=api_key)

registration_ids= ["f7fHfPD0Q0eFavzB_yp4NE:REDACTED_FCM_TOKEN",]
# Sending a notification with data message payload
data_message = {}

message_body = "Firdous here"


registration_id = "fL_mFnfASkuUQ72Yr2GSUq:REDACTED_FCM_TOKEN"


# name = "MPPSC"
# message_title = 'Payment successful'

# message_body = "You have successfully purchased the "+name+ " course.\n Happy Learning "
# result = push_service.notify_single_device(registration_id=registration_id, message_title=message_title, message_body=message_body)   
                                

# print(result)
# # To multiple devices
# result = push_service.notify_multiple_devices(
#     registration_ids=registration_ids,
#     message_body=message_body,
#     data_message=data_message
# )

