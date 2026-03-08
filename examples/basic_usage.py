"""Basic usage of the SanctumAI Python SDK."""

from sanctum_ai import SanctumClient

# Connect via default Unix socket (~/.sanctum/vault.sock)
with SanctumClient("my-agent") as client:
    # List available credentials
    credentials = client.list()
    print("Available credentials:", credentials)

    # Use-don't-retrieve: make an API call through the vault.
    # The API key is injected server-side — it never enters this process.
    response = client.use_credential("openai/api-key", "http_request", {
        "method": "POST",
        "url": "https://api.openai.com/v1/chat/completions",
        "headers": {"Content-Type": "application/json"},
        "body": '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}',
        "header_type": "bearer",
    })
    print("Status:", response["status"])
    print("Body:", response["body"])
