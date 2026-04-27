from functools import lru_cache
from typing import Optional

import vimeo

from configs import appinfo


@lru_cache()
def app_setting():
    return appinfo.Setting()


def get_vimeo_client() -> Optional[vimeo.VimeoClient]:
    settings = app_setting()
    if not (
        settings.vimeo_access_token
        and settings.vimeo_client_id
        and settings.vimeo_client_secret
    ):
        return None

    return vimeo.VimeoClient(
        token=settings.vimeo_access_token,
        key=settings.vimeo_client_id,
        secret=settings.vimeo_client_secret,
    )
