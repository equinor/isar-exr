from time import sleep

from gql.transport.exceptions import TransportError
from graphql import GraphQLError

from isar_exr.api.graphql_client import GraphqlClient

graph_client: GraphqlClient = GraphqlClient()

# Provide a GraphQL query
query_string = """
    query queryName {
      robotFleet {
        id
      }
    }
"""

# Execute the query on the transport
while True:
    print()
    try:
        result = graph_client.query(query_string)
        print()
        print(result)
    except GraphQLError as e:
        print(f"Error during query: {e.message}")
    except TransportError as e:
        print(f"Error during communcation with server: {e}")

    sleep(2)
