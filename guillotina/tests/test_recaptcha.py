from guillotina import app_settings
from guillotina.auth.recaptcha import RECAPTCHA_VALIDATION_URL
from guillotina.auth.recaptcha import RecaptchaValidator
from guillotina.auth.recaptcha import VALIDATION_HEADER
from guillotina.component import query_utility
from guillotina.interfaces.async_util import IRecaptchaValidationUtility
from guillotina.tests import utils
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import json
import pytest


pytestmark = pytest.mark.asyncio

FAKE_RECAPTCHA = "FAKE_RECAPTCHA"


class TestRecaptchaValidator:
    """Test the RecaptchaValidator utility class directly."""

    async def test_initialize_and_finalize(self):
        """Test that initialize and finalize methods exist and work."""
        validator = RecaptchaValidator()
        await validator.initialize()
        await validator.finalize()

    async def test_validate_with_fake_recaptcha(self):
        """Test validation with fake recaptcha token."""
        app_settings["_fake_recaptcha_"] = FAKE_RECAPTCHA
        request = utils.get_mocked_request(headers={VALIDATION_HEADER: FAKE_RECAPTCHA})
        utils.task_vars.request.set(request)

        validator = RecaptchaValidator()
        result = await validator.validate()
        assert result is True

    async def test_validate_without_configuration(self):
        """Test validation when recaptcha is not configured (graceful degradation)."""
        app_settings.pop("recaptcha", None)
        request = utils.get_mocked_request(headers={VALIDATION_HEADER: "some-token"})
        utils.task_vars.request.set(request)

        validator = RecaptchaValidator()
        result = await validator.validate()
        # Should return True when not configured (graceful degradation)
        assert result is True

    async def test_validate_success(self):
        """Test successful validation with mocked HTTP response."""
        app_settings["recaptcha"] = {"private": "test-secret-key"}
        request = utils.get_mocked_request(headers={VALIDATION_HEADER: "valid-token"})
        utils.task_vars.request.set(request)

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_post = AsyncMock(return_value=mock_response)
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("guillotina.auth.recaptcha.aiohttp.ClientSession", return_value=mock_session):
            validator = RecaptchaValidator()
            result = await validator.validate()

            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == RECAPTCHA_VALIDATION_URL
            assert call_args[1]["data"]["secret"] == "test-secret-key"
            assert call_args[1]["data"]["response"] == "valid-token"

    async def test_validate_failure(self):
        """Test failed validation with mocked HTTP response."""
        app_settings["recaptcha"] = {"private": "test-secret-key"}
        request = utils.get_mocked_request(headers={VALIDATION_HEADER: "invalid-token"})
        utils.task_vars.request.set(request)

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"success": False})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_post = AsyncMock(return_value=mock_response)
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("guillotina.auth.recaptcha.aiohttp.ClientSession", return_value=mock_session):
            validator = RecaptchaValidator()
            result = await validator.validate()

            assert result is False

    async def test_validate_error_handling(self):
        """Test validation error handling (JSON decode error, missing success key)."""
        app_settings["recaptcha"] = {"private": "test-secret-key"}
        request = utils.get_mocked_request(headers={VALIDATION_HEADER: "some-token"})
        utils.task_vars.request.set(request)

        # Test JSON decode error
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_post = AsyncMock(return_value=mock_response)
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("guillotina.auth.recaptcha.aiohttp.ClientSession", return_value=mock_session):
            validator = RecaptchaValidator()
            result = await validator.validate()
            assert result is False

        # Test missing success key
        mock_response.json = AsyncMock(return_value={})
        with patch("guillotina.auth.recaptcha.aiohttp.ClientSession", return_value=mock_session):
            validator = RecaptchaValidator()
            result = await validator.validate()
            assert result is False


class TestRecaptchaUtilityIntegration:
    """Test the utility pattern integration."""

    async def test_utility_registered_and_implements_interface(self):
        """Test that the utility is registered and implements the interface."""
        from zope.interface.verify import verifyObject

        utility = query_utility(IRecaptchaValidationUtility)
        assert utility is not None
        assert isinstance(utility, RecaptchaValidator)
        assert verifyObject(IRecaptchaValidationUtility, utility)


class TestRecaptchaEndpointIntegration:
    """Test endpoints that use reCAPTCHA validation."""

    @pytest.mark.app_settings({"_fake_recaptcha_": FAKE_RECAPTCHA})
    async def test_endpoint_rejects_invalid_recaptcha(self, container_requester):
        """Test that endpoints reject requests with invalid reCAPTCHA."""
        async with container_requester as requester:
            # Mock the utility to return False
            utility = query_utility(IRecaptchaValidationUtility)
            original_validate = utility.validate
            utility.validate = AsyncMock(return_value=False)

            try:
                # Test @info endpoint
                _, status = await requester(
                    "GET",
                    "/db/guillotina/@info",
                    authenticated=False,
                    headers={VALIDATION_HEADER: "invalid-token"},
                )
                assert status == 401

                # Test @users registration endpoint
                _, status = await requester(
                    "POST",
                    "/db/guillotina/@users",
                    data=json.dumps(
                        {
                            "id": "testuser@example.com",
                            "email": "testuser@example.com",
                            "password": "testpassword",
                            "fullname": "Test User",
                        }
                    ),
                    authenticated=False,
                    headers={VALIDATION_HEADER: "invalid-token"},
                )
                assert status == 401
            finally:
                utility.validate = original_validate
