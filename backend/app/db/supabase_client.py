from app.core.config import settings
from app.db.mock_db import mock_supabase


def has_supabase_credentials() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


if settings.AFP_USE_MOCK_DB:
    supabase = mock_supabase
else:
    if not has_supabase_credentials():
        raise RuntimeError(
            "Supabase credentials are required. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY, or explicitly set AFP_USE_MOCK_DB=true "
            "for isolated development."
        )
    import httpx
    from supabase import create_client, ClientOptions

    # Configure a custom HTTP client with retries and an increased timeout
    # to prevent WinError 10035 (WSAEWOULDBLOCK) and other transient socket errors on Windows.
    transport = httpx.HTTPTransport(retries=3)
    httpx_client = httpx.Client(transport=transport, timeout=30.0)
    options = ClientOptions(httpx_client=httpx_client)

    supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        options=options
    )

