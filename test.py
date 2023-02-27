import json
import os

import requests
from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from requests.auth import HTTPBasicAuth

load_dotenv()
username = os.getenv("API_USERNAME")
password = os.getenv("API_PASSWORD")
url = "https://login.energy-robotics.com/api/loginApi"
r = requests.post(
    url,
    auth=HTTPBasicAuth(username=username, password=password),
)
jsonrespons = json.loads(r.content.decode("utf-8"))
token = jsonrespons["access_token"]
reqHeaders = {
    "authorization": "Bearer " + token,
}
transport = AIOHTTPTransport(
    url="https://developer.energy-robotics.com/graphql", headers=reqHeaders
)

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
