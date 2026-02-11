"""Example: integrating SanctumAI into an AI agent framework."""

from sanctum_ai import SanctumClient, VaultError, AccessDenied, LeaseExpired


def run_agent():
    client = SanctumClient(
        "research-agent",
        # TCP connection instead of Unix socket:
        host="127.0.0.1",
        port=8200,
        # Explicit key path (optional):
        # key_path="~/.sanctum/keys/research-agent.key",
    )

    try:
        client.connect()

        # Retrieve with a custom TTL (seconds)
        api_key = client.retrieve("anthropic/api_key", ttl=300)
        print(f"Got key (lease expires in 5 min): {api_key[:8]}...")

        # Get full lease info
        raw = client.retrieve_raw("openai/api_key", ttl=600)
        print(f"Lease ID: {raw['lease_id']}, TTL: {raw.get('ttl')}s")

        # Explicitly release when done early
        client.release_lease(raw["lease_id"])

    except AccessDenied as e:
        print(f"Access denied: {e} (suggestion: {e.suggestion})")
    except LeaseExpired as e:
        print(f"Lease expired: {e}")
    except VaultError as e:
        print(f"Vault error [{e.code}]: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    run_agent()
