"""Example: integrating SanctumAI into an AI agent framework."""

from sanctum_ai import SanctumClient, VaultError, AccessDenied, CredentialNotFound

def run_agent():
    client = SanctumClient(
        "research-agent",
        host="127.0.0.1",
        port=7600,
    )

    try:
        client.connect()

        # --- use_credential: proxy an HTTP request ---
        # The vault injects the API key and makes the request for you.
        result = client.use_credential("openai/api-key", "http_request", {
            "method": "POST",
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": {"Content-Type": "application/json"},
            "body": '{"model": "gpt-4", "messages": [{"role": "user", "content": "Summarize quantum computing"}]}',
            "header_type": "bearer",
        })
        print(f"OpenAI response status: {result['status']}")

        # --- use_credential: get an HTTP header for custom requests ---
        header = client.use_credential("github/token", "http_header", {
            "header_type": "bearer",
        })
        print(f"Got header: {header['header_name']}")

        # --- use_credential: HMAC signing ---
        signed = client.use_credential("webhook/secret", "sign", {
            "algorithm": "hmac-sha256",
            "data": "event-payload",
        })
        print(f"Signature: {signed['signature']}")

        # --- retrieve: when you need the raw value ---
        api_key = client.retrieve("anthropic/api-key", ttl=300)
        print(f"Got key (lease expires in 5 min): {api_key[:8]}...")

    except AccessDenied as e:
        print(f"Access denied: {e} (suggestion: {e.suggestion})")
    except CredentialNotFound as e:
        print(f"Credential not found: {e}")
    except VaultError as e:
        print(f"Vault error [{e.code}]: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    run_agent()
