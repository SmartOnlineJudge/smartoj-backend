from elasticsearch import AsyncElasticsearch

import settings


DEFAULT_ES_CONFIG = settings.ELASTICSEARCH_CONF["default"]


client = AsyncElasticsearch(
    hosts=DEFAULT_ES_CONFIG["URL"],
    basic_auth=(DEFAULT_ES_CONFIG["USER"], DEFAULT_ES_CONFIG["PASSWORD"])
)
