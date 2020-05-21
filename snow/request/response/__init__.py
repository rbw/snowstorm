from typing import Any, Iterable, Union

from aiohttp import ClientResponse, client_exceptions, http_exceptions, web_exceptions
from marshmallow import EXCLUDE

from snow.exceptions import RequestError, ServerError, UnexpectedResponseContent

from .schemas import ContentSchema, ErrorSchema


class Response(ClientResponse):
    """Snow Response class

    Deserializes the response content received from a ServiceNow API

    Subclass of aiohttp.ClientResponse, its base reference documentation can be found here:
    https://docs.aiohttp.org/en/latest/client_reference.html#aiohttp.ClientResponse

    Attributes:
        - data: Deserialized (ContentSchema) response content
        - status: HTTP status code of response (int), e.g. 200
        - reason: HTTP status reason of response (str), e.g. "OK"
        - url: Request URL
    """

    data: Union[list, dict]

    def __repr__(self) -> str:
        if isinstance(self.data, list):
            content_overview = f"Content: List of {len(self.data)} items"
        elif self.data and isinstance(self.data, dict):
            content_overview = "Content: Object contained in a dictionary"
        else:
            content_overview = "Content: Unknown"

        return (
            f"<{self.__class__.__name__} {hex(id(self))} {self.url.path} "
            f"[{self.status} {self.reason}] {content_overview}>"
        )

    def __getitem__(self, key: Any) -> Any:
        return self.data[key]

    def __iter__(self) -> Iterable:
        yield from self.data

    def __len__(self) -> int:
        if isinstance(self.data, list):
            return len(self.data)

        return 1

    async def load(self) -> None:
        """Deserialize and set response content

        Raises:
            RequestError: If there was an error in the request-response content
        """

        data = await self.json()

        if not isinstance(data, dict):
            if self.status == 204:
                self.data = {}
                return

            await self._handle_error()

        content = ContentSchema(unknown=EXCLUDE, many=False).load(data)
        if "error" in content:
            err = content["error"]
            msg = (
                f"{err['message']}: {err['detail']}"
                if err["detail"]
                else err["message"]
            )

            raise RequestError(msg, self.status)

        self.data = content["result"]

    async def _handle_error(self) -> None:
        """Something went seriously wrong.

        This method interprets the error-response and raises the appropriate exception.

        Raises:
            - ServerError: If the error was interpreted as an unhandled server error
            - UnexpectedResponseContent: If the request was successful, but the request-response contains
            unexpected data
        """

        try:
            # Something went wrong, most likely out of the ServiceNow application's control:
            # Raise exception if we got a HTTP error status back.
            self.raise_for_status()
        except (
            client_exceptions.ClientResponseError,
            http_exceptions.HttpProcessingError,
        ) as exc:
            raise ServerError(exc.message, exc.code) from exc
        except web_exceptions.HTTPException as exc:
            raise ServerError(exc.text or "", exc.status) from exc
        else:
            # Non-JSON content along with a HTTP 200 returned: Unexpected.
            text = await self.text()
            raise UnexpectedResponseContent(
                f"Unexpected response received from server: {text}", 200
            )