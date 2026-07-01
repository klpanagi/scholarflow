"""Elasticsearch search service for papers and chunks."""

from typing import Optional
from elasticsearch import AsyncElasticsearch

from ..core.config import settings


class SearchService:
    """Elasticsearch hybrid search with BM25 + kNN vectors."""

    def __init__(self):
        self._es: Optional[AsyncElasticsearch] = None

    async def _get_es(self) -> AsyncElasticsearch:
        if self._es is None:
            self._es = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
        return self._es

    async def close(self):
        if self._es:
            await self._es.close()
            self._es = None

    async def ensure_indices(self):
        """Create indices if they don't exist."""
        client = await self._get_es()
        for index, mapping in [
            (settings.ELASTICSEARCH_PAPERS_INDEX, PAPERS_INDEX_MAPPING),
            (settings.ELASTICSEARCH_CHUNKS_INDEX, CHUNKS_INDEX_MAPPING),
        ]:
            if not await client.indices.exists(index=index):
                await client.indices.create(index=index, body=mapping)

    async def embed_text(self, text: str) -> list[float]:
        from app.services.llm_service import llm_service
        from app.core.database import AsyncSessionLocal
        from app.services.system_settings import get_setting

        provider = settings.EMBEDDING_PROVIDER
        model = settings.EMBEDDING_MODEL
        try:
            async with AsyncSessionLocal() as db:
                db_provider = await get_setting(db, "embedding_provider")
                db_model = await get_setting(db, "embedding_model")
                if db_provider:
                    provider = db_provider
                if db_model:
                    model = db_model
        except Exception:
            pass

        result = await llm_service.get_embedding(
            model=model,
            texts=[text],
            provider=provider,
        )
        return result[0]

    async def index_document(
        self,
        index: str,
        doc_id: str,
        document: dict,
        embedding: list[float] | None = None,
    ) -> str:
        """Index a document in Elasticsearch."""
        client = await self._get_es()
        if embedding:
            document["embedding"] = embedding
        resp = await client.index(
            index=index,
            id=doc_id,
            document=document,
            refresh=True,
        )
        return resp["_id"]

    async def search(
        self,
        query: str,
        index: str | None = None,
        limit: int = 20,
        owner_filter: str | None = None,
        embedding: list[float] | None = None,
    ) -> list[dict]:
        """Search documents with BM25 and optional vector search."""
        client = await self._get_es()
        search_index = index or settings.ELASTICSEARCH_PAPERS_INDEX

        must_clause = []
        if owner_filter:
            must_clause.append({"term": {"owner_id.keyword": owner_filter}})

        search_body: dict = {
            "size": limit,
            "query": {
                "bool": {
                    "must": must_clause if must_clause else [{"match_all": {}}],
                    "should": [{
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "abstract^2", "content^2", "text^2"],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        }
                    }],
                    "minimum_should_match": 1,
                }
            },
            "highlight": {
                "fields": {
                    "title": {},
                    "abstract": {},
                    "content": {},
                    "text": {},
                }
            },
        }

        # kNN must be at the top level of the search body (ES 8.x syntax),
        # not nested inside bool.should.
        if embedding:
            search_body["knn"] = {
                "field": "embedding",
                "query_vector": embedding,
                "k": limit,
                "num_candidates": limit * 10,
            }

        resp = await client.search(index=search_index, body=search_body)

        results = []
        for hit in resp["hits"]["hits"]:
            results.append({
                "document": hit["_source"],
                "score": hit["_score"],
                "highlights": hit.get("highlight", {}),
            })
        return results

    async def delete_document(self, index: str, doc_id: str):
        """Delete a document by ID."""
        client = await self._get_es()
        await client.delete(index=index, id=doc_id, ignore=[404])

    async def delete_by_query(self, index: str, field: str, value: str):
        """Delete documents matching a query."""
        client = await self._get_es()
        await client.delete_by_query(
            index=index,
            body={"query": {"term": {field: value}}},
        )


PAPERS_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "owner_id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "standard"},
            "authors": {"type": "keyword"},
            "abstract": {"type": "text", "analyzer": "standard"},
            "doi": {"type": "keyword"},
            "arxiv_id": {"type": "keyword"},
            "year": {"type": "integer"},
            "venue": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "embedding": {
                "type": "dense_vector",
                "dims": 1536,
                "index": True,
                "similarity": "cosine",
            },
            "created_at": {"type": "date"},
        }
    }
}

CHUNKS_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "asset_id": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "content": {"type": "text", "analyzer": "standard"},
            "title": {"type": "text", "analyzer": "standard"},
            "owner_id": {"type": "keyword"},
            "embedding": {
                "type": "dense_vector",
                "dims": 1536,
                "index": True,
                "similarity": "cosine",
            },
        }
    }
}


search_service = SearchService()
