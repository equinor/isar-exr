import logging
from typing import Any, Dict
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import (
    TransportClosed,
    TransportQueryError,
    TransportServerError,
    TransportProtocolError,
)
from graphql import GraphQLError
from isar_exr.api.authentication import get_access_token
from isar_exr.config.settings import settings


class GraphqlClient:
    def __init__(self):
        # Parameter used for retrying query with new authentication
        # in case of expired token
        self._reauthenticated = False
        self.logger = logging.getLogger("graphql_client")
        self._initialize_client()

    def _initialize_client(self):
        try:
            token: str = get_access_token()
        except Exception as e:
            self.logger.critical(f"CRITICAL - Error getting access token: \n{e}")
            raise
        auth_header = {
            "authorization": "Bearer " + token,
        }
        transport = AIOHTTPTransport(url=settings.ROBOT_API_URL, headers=auth_header)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def query(self, json_body: str) -> Dict[str, Any]:
        """
        Sends a GraphQL query to the 'ROBOT_API_URL' endpoint.

        :return: A dictionary of the object returned from the API if success.

        :raises GrahpQLError: Something went related to the query
        :raises TransportError: Something went wrong during transfer or on the API server side
        :raises Exception: Unknown error
        """
        query = gql(json_body)
        try:
            response: Dict[str, Any] = self.client.execute(query)
            return response
        except GraphQLError as e:
            self.logger.error(
                f"Something went wrong while sending the GraphQL query: {e.message}"
            )
            raise
        except TransportProtocolError as e:
            if self._reauthenticated:
                self.logger.error(
                    "Transport protocol error - Error in configuration of GraphQL client"
                )
                raise
            else:
                # The token might have expired, try again with a new token
                self._initialize_client()
                self._reauthenticated = True
                self.query(json_body=json_body)
        except TransportQueryError as e:
            self.logger.error(
                f"The Energy Robotics server returned an error: {e.errors}"
            )
            raise
        except TransportClosed as e:
            self.logger.error("The connection to the GraphQL endpoint is closed")
            raise
        except TransportServerError as e:
            self.logger.error(f"Error in Energy Robotics server: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unknown error in GraphQL client: {e}")
            raise
        finally:
            self._reauthenticated = False
        return None
