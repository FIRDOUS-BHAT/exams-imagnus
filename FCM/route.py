from functools import lru_cache
from typing import Any, Optional

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pyfcm import FCMNotification

from configs import appinfo
from student.models import Student

router = APIRouter()


@lru_cache()
def app_setting():
    return appinfo.Setting()


class PushNotificationService:
    def __init__(self, api_key: str = ""):
        self._client: Optional[FCMNotification] = (
            FCMNotification(api_key=api_key) if api_key else None
        )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def notify_single_device(self, *args: Any, **kwargs: Any):
        if not self._client:
            return None
        return self._client.notify_single_device(*args, **kwargs)

    def notify_multiple_devices(self, *args: Any, **kwargs: Any):
        if not self._client:
            return None
        return self._client.notify_multiple_devices(*args, **kwargs)


settings = app_setting()
push_service = PushNotificationService(settings.fcm_server_key)


@router.post("/send_app_update_notification/")
async def send_app_update_notification():
    if not push_service.is_configured:
        return JSONResponse(
            {"status": False, "message": "Push notifications are not configured."},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        fcm_list = await Student.all().values("fcm_token")
        registration_ids = [row["fcm_token"] for row in fcm_list if row.get("fcm_token")]

        if not registration_ids:
            return JSONResponse({"status": True, "message": "No devices to notify."})

        extra_notification_kwargs = {
            "open": "external_url",
            "data_payload": "https://play.google.com/store/apps/details?id=com.smcln.imagnus",
        }
        message_body = (
            "Dear student,\n\n"
            "There is an app update available. Please tap here to open the app link. "
            "Ignore this notification if you already updated the app to the newest version."
        )
        push_service.notify_multiple_devices(
            registration_ids=registration_ids,
            message_icon="app_icon",
            message_title="I-Magnus app update available",
            message_body=message_body,
            click_action="FLUTTER_NOTIFICATION_CLICK",
            data_message=extra_notification_kwargs,
        )

        return JSONResponse({"status": True, "message": "Notifications sent."})

    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)
