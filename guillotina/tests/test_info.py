import pytest
from guillotina.auth.recaptcha import VALIDATION_HEADER

pytestmark = pytest.mark.asyncio

FAKE_RECAPTCHA = "FAKE_RECAPTCHA"


@pytest.mark.app_settings({"_fake_recaptcha_": FAKE_RECAPTCHA})
async def test_get_public_info(container_requester):
    async with container_requester as requester:
        response, _ = await requester(
            "GET", "/db/guillotina/@info", authenticated=False, headers={VALIDATION_HEADER: FAKE_RECAPTCHA}
        )
        assert response["register"] is False
        assert len(response["social"]) == 0
        assert response["title"] == "Guillotina Container"


async def test_get_public_info_no_recaptcha(container_requester):
    async with container_requester as requester:
        response, _ = await requester("GET", "/db/guillotina/@info", authenticated=False)
        assert response["register"] is False
        assert len(response["social"]) == 0
        assert response["title"] == "Guillotina Container"


@pytest.mark.app_settings({"allow_register": True})
async def test_get_public_info_no_recaptcha_register(container_requester):
    async with container_requester as requester:
        response, _ = await requester("GET", "/db/guillotina/@info", authenticated=False)
        assert response["register"] is True
        assert len(response["social"]) == 0
        assert response["title"] == "Guillotina Container"
