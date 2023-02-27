import json
import requests
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from requests.auth import HTTPBasicAuth
from isar_exr.config.settings import settings

username = settings.ROBOT_API_USERNAME
password = settings.ROBOT_API_PASSWORD
auth_url = settings.ROBOT_AUTH_URL
r = requests.post(
    auth_url,
    auth=HTTPBasicAuth(username=username, password=password),
)
jsonrespons = json.loads(r.content.decode("utf-8"))
token = jsonrespons["access_token"]
reqHeaders = {
    "authorization": "Bearer " + token,
}
transport = AIOHTTPTransport(url=settings.ROBOT_API_URL, headers=reqHeaders)

# Create a GraphQL client using the defined transport
client = Client(transport=transport, fetch_schema_from_transport=True)

# Provide a GraphQL query
query = gql(
    """
    query robotFleet {
      robotFleet {
        id
      }
    }
"""
)

# Execute the query on the transport
result = client.execute(query)
print(result)
