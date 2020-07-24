import aiohttp
import pytest

from aiosnow.client import Client
from aiosnow.exceptions import ConfigurationException, IncompatibleSession
from aiosnow.request.response import Response
from aiosnow.session import Session


def test_client_session_invalid_type():
    """Invalid object type passed to `session` should raise an InvalidSessionType exception"""

    fail_str = dict(address="test.service-now.com", session="test")
    fail_int = dict(address="test.service-now.com", session=123)

    with pytest.raises(IncompatibleSession):
        Client(**fail_str)
        Client(**fail_int)


def test_client_session_mutual_exclusive():
    """Passing both a session and session factory configuration should raise ConfigurationException"""

    session = Session()

    with pytest.raises(ConfigurationException):
        Client("test.service-now.com", session=session, basic_auth=("a", "b"))

    with pytest.raises(ConfigurationException):
        Client("test.service-now.com", session=session, verify_ssl=True)


def test_client_session_no_auth_method():
    """No authentication method to Client should raise ConfigurationException"""

    with pytest.raises(ConfigurationException):
        Client("test.service-now.com")


def test_client_session_config_full():
    """Session config should load into a config object"""

    config = dict(
        address="test.service-now.com",
        basic_auth=("test", "test"),
        use_ssl=True,
        verify_ssl=True,
    )

    snow = Client(**config)

    assert snow.config.address == config["address"]
    assert snow.config.session.basic_auth == config["basic_auth"]
    assert snow.config.session.use_ssl == config["use_ssl"]
    assert snow.config.session.verify_ssl == config["verify_ssl"]


def test_client_session_object():
    """Compatible user-provided Session objects should be returned from Client.get_session"""

    session = Session()
    snow = Client("test.service-now.com", session=session)
    assert snow.get_session() == snow._preconf_session == session


def test_client_session_invalid_response_class():
    """Compatible user-provided Session objects should be returned from Client.get_session"""

    session = aiohttp.ClientSession()

    with pytest.raises(IncompatibleSession):
        Client("test.service-now.com", session=session)


def test_client_session_response_class():
    """Compatible user-provided Session objects should be returned from Client.get_session"""

    session = aiohttp.ClientSession(response_class=Response)
    snow = Client("test.service-now.com", session=session)

    assert snow.get_session()._response_class == Response