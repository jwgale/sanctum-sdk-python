"""Basic usage of the SanctumAI Python SDK."""

from sanctum_ai import SanctumClient

# Connect via default Unix socket (~/.sanctum/vault.sock)
with SanctumClient("my-agent") as client:
    # List available credentials
    credentials = client.list()
    print("Available credentials:", credentials)

    # Retrieve a secret
    api_key = client.retrieve("openai/api_key")
    print("Got API key:", api_key[:8] + "...")

    # Use-not-retrieve pattern (credential never leaves the vault)
    result = client.use("openai/api_key", "http_header")
    print("Header:", result)
