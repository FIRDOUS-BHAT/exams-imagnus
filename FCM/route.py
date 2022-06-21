# Send to single device.
from fastapi import APIRouter
from pyfcm import FCMNotification
from fastapi.responses import JSONResponse

from student.models import Student

router = APIRouter()


api_key = "REDACTED_FCM_SERVER_KEY"
push_service = FCMNotification(api_key=api_key)

registration_ids = [
    "f7fHfPD0Q0eFavzB_yp4NE:REDACTED_FCM_TOKEN", ]
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


@router.post('/send_app_update_notification/')
async def send_app_update_notification():
    try:
        fcm_list = await Student.all().values("fcm_token")
        fcms = list(map(lambda x: x['fcm_token'], fcm_list))
        registration_ids = list(filter(None, fcms))
        registration_ids = [
            "dxjNGZ5vT6WuDe4e5EScgE:REDACTED_FCM_TOKEN"]

        message_title = "imagnus app update available"

        extra_notification_kwargs = {
            "open": "external_url",
            "data_payload": "https://play.google.com/store/apps/details?id=com.smcln.imagnus"
        }
        data_message = "Dear student, \n\n There is an app update available. Please tap here to go to open the  app link. Ignore this notification if you already updated app to the newest version."
        result = push_service.notify_multiple_devices(
            registration_ids=registration_ids,
            message_icon="app_icon",
            message_title=message_title,
            message_body=data_message,
            click_action="FLUTTER_NOTIFICATION_CLICK",
            data_message=extra_notification_kwargs,
        )

        return JSONResponse({"status": True, "message": "Notifications sent."})

    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)})
