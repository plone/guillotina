from guillotina import app_settings
from guillotina.utils import get_current_request

import logging


logger = logging.getLogger("guillotina")

RECAPTCHA_VALIDATION_URL = "https://www.google.com/recaptcha/api/siteverify"
VALIDATION_HEADER = "X-VALIDATION-G"


class RecaptchaValidator:
    # Not valid to generate a user
    for_validators = ()

    async def validate(self):
        request = get_current_request()
        token = request.headers.get(VALIDATION_HEADER)

        if token == app_settings.get("_fake_recaptcha_") and token is not None:
            return True
        if app_settings.get("recaptcha") is None or app_settings["recaptcha"].get("private") is None:
            logger.warning("Validating with recaptcha and no configuration found")
            return True

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with await session.post(
                RECAPTCHA_VALIDATION_URL,
                data=dict(secret=app_settings["recaptcha"]["private"], response=token),
            ) as resp:
                try:
                    data = await resp.json()
                except Exception:  # pragma: no cover
                    logger.warning("Did not get json response", exc_info=True)
                    return
                try:
                    return data["success"]
                except Exception:  # pragma: no cover
                    return False
