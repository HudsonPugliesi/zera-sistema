import ssl


def normalizar_postgres_url(url):
    """Ajusta uma URL de Postgres para usar o driver pg8000 (puro Python,
    sem dependência de biblioteca nativa — evita falhas em ambientes
    serverless como o da Vercel).

    Retorna (url_normalizada, engine_kwargs), onde engine_kwargs já traz o
    connect_args com SSL habilitado quando necessário.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    engine_kwargs = {}
    if url.startswith("postgresql://"):
        # pg8000 não entende parâmetros de libpq como "sslmode"/"channel_binding"
        # na query string, então removemos e habilitamos SSL via connect_args.
        url = url.split("?")[0].replace("postgresql://", "postgresql+pg8000://", 1)
        engine_kwargs["connect_args"] = {"ssl_context": ssl.create_default_context()}

    return url, engine_kwargs
