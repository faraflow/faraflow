# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
"""
Chroma datastore support for the ChatGPT retrieval plugin.

Consult the Chroma docs and GitHub repo for more information:
- https://docs.trychroma.com/usage-guide?lang=py
- https://github.com/chroma-core/chroma
- https://www.trychroma.com/
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlsplit

import chromadb

from ...chunker import create_document_chunks
from ...schemas.document_schemas import (
    ChunkingConfigSchema,
    DocumentChunkMetadataSchema,
    DocumentChunkSchema,
    DocumentChunkWithScoreSchema,
    DocumentMetadataFilterSchema,
    DocumentSchema,
    QueryResultSchema,
    QueryWithEmbeddingSchema,
    Source,
)
from ..datastore import DataStore

CHROMA_IN_MEMORY = os.environ.get("CHROMA_IN_MEMORY", "True")
# Under backend/data, which docker-compose keeps in a named volume.
CHROMA_PERSISTENCE_DIR = os.environ.get("CHROMA_PERSISTENCE_DIR", "data/chroma")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://127.0.0.1")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "openaiembeddings")


class ChromaDataStore(DataStore):
    def __init__(
        self,
        embedding_dimension: Optional[int] = None,
        in_memory: Optional[bool] = None,
        persistence_dir: Optional[str] = CHROMA_PERSISTENCE_DIR,
        collection_name: str = CHROMA_COLLECTION,
        host: str = CHROMA_HOST,
        port: str = CHROMA_PORT,
        client: Optional[chromadb.Client] = None,
    ):
        super().__init__(embedding_dimension=embedding_dimension)
        if client:
            self._client = client
        else:
            if in_memory is None:
                in_memory = CHROMA_IN_MEMORY.strip().lower() in ("1", "true", "yes", "on")
            settings = chromadb.config.Settings(anonymized_telemetry=False)
            if in_memory:
                # "In memory" means a local client: persisted to disk when a directory is set.
                if persistence_dir:
                    self._client = chromadb.PersistentClient(path=persistence_dir, settings=settings)
                else:
                    self._client = chromadb.EphemeralClient(settings=settings)
            else:
                url = urlsplit(host if "://" in host else f"http://{host}")
                self._client = chromadb.HttpClient(
                    host=url.hostname or "127.0.0.1",
                    port=int(port),
                    ssl=url.scheme == "https",
                    settings=settings,
                )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
        )

    async def upsert(
        self,
        documents: List[DocumentSchema],
        chunk_token_size: Optional[int] = None,
    ) -> List[str]:
        """
        Takes in a list of documents and inserts them into the database. If an id already exists, the document is updated.
        Return a list of document ids.
        """
        chunks = {}
        for doc in documents:
            existing = getattr(doc, "chunks", None)
            if existing and all(chunk.embedding is not None for chunk in existing):
                # The vector index already chunked and embedded this document: keep those chunks.
                chunks[doc.id or existing[0].metadata.document_id] = existing
                continue
            config = (
                ChunkingConfigSchema(chunk_token_size=chunk_token_size)
                if chunk_token_size
                else ChunkingConfigSchema()
            )
            doc_chunks, doc_id = create_document_chunks(doc, config)
            chunks[doc_id] = doc_chunks

        # Chroma has a true upsert, so we don't need to delete first
        return await self._upsert(chunks)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunkSchema]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """

        self._collection.upsert(
            ids=[chunk.id for chunk_list in chunks.values() for chunk in chunk_list],
            embeddings=[chunk.embedding for chunk_list in chunks.values() for chunk in chunk_list],
            documents=[chunk.text for chunk_list in chunks.values() for chunk in chunk_list],
            metadatas=[
                self._process_metadata_for_storage(chunk.metadata)
                for chunk_list in chunks.values()
                for chunk in chunk_list
            ],
        )
        return list(chunks.keys())

    @staticmethod
    def _normalize_where(where: Optional[Dict]) -> Optional[Dict]:
        """Chroma rejects an empty filter and a filter with several keys, so adapt both."""
        if not where:
            return None
        if len(where) == 1:
            return where
        return {"$and": [{key: value} for key, value in where.items()]}

    def _where_from_query_filter(self, query_filter: DocumentMetadataFilterSchema) -> Dict:
        output = {
            k: v
            for (k, v) in query_filter.dict().items()
            if v is not None and k != "start_date" and k != "end_date" and k != "source"
        }
        if query_filter.source:
            output["source"] = query_filter.source.value
        if query_filter.start_date and query_filter.end_date:
            output["$and"] = [
                {
                    "created_at": {
                        "$gte": int(datetime.fromisoformat(query_filter.start_date).timestamp())
                    }
                },
                {
                    "created_at": {
                        "$lte": int(datetime.fromisoformat(query_filter.end_date).timestamp())
                    }
                },
            ]
        elif query_filter.start_date:
            output["created_at"] = {
                "$gte": int(datetime.fromisoformat(query_filter.start_date).timestamp())
            }
        elif query_filter.end_date:
            output["created_at"] = {
                "$lte": int(datetime.fromisoformat(query_filter.end_date).timestamp())
            }

        return output

    def _process_metadata_for_storage(self, metadata: DocumentChunkMetadataSchema) -> Dict:
        stored_metadata = {}
        if metadata.source:
            stored_metadata["source"] = metadata.source.value
        if metadata.source_id:
            stored_metadata["source_id"] = metadata.source_id
        if metadata.title:
            stored_metadata["title"] = metadata.title
        if metadata.chunk_index is not None:
            stored_metadata["chunk_index"] = metadata.chunk_index
        if metadata.created_at:
            stored_metadata["created_at"] = int(
                datetime.fromisoformat(metadata.created_at).timestamp()
            )
        if metadata.author:
            stored_metadata["author"] = metadata.author
        if metadata.document_id:
            stored_metadata["document_id"] = metadata.document_id

        return stored_metadata

    def _process_metadata_from_storage(self, metadata: Dict) -> DocumentChunkMetadataSchema:
        return DocumentChunkMetadataSchema(
            source=Source(metadata["source"]) if "source" in metadata else None,
            source_id=metadata.get("source_id", None),
            title=metadata.get("title", None),
            chunk_index=metadata.get("chunk_index", None),
            created_at=(
                datetime.fromtimestamp(metadata["created_at"]).isoformat()
                if "created_at" in metadata
                else None
            ),
            author=metadata.get("author", None),
            document_id=metadata.get("document_id", None),
        )

    async def _query(self, queries: List[QueryWithEmbeddingSchema]) -> List[QueryResultSchema]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        results = [
            self._collection.query(
                query_embeddings=[query.embedding],
                include=["documents", "distances", "metadatas"],  # embeddings
                n_results=min(query.top_k, self._collection.count()),  # type: ignore
                where=self._normalize_where(
                    self._where_from_query_filter(query.filter) if query.filter else None
                ),
            )
            for query in queries
        ]

        output = []
        for query, result in zip(queries, results):
            inner_results = []
            (ids,) = result["ids"]
            # (embeddings,) = result["embeddings"]
            (documents,) = result["documents"]
            (metadatas,) = result["metadatas"]
            (distances,) = result["distances"]
            for id_, text, metadata, distance in zip(
                ids,
                documents,
                metadatas,
                distances,  # embeddings (https://github.com/openai/chatgpt-retrieval-plugin/pull/59#discussion_r1154985153)
            ):
                inner_results.append(
                    DocumentChunkWithScoreSchema(
                        id=id_,
                        text=text,
                        metadata=self._process_metadata_from_storage(metadata),
                        # embedding=embedding,
                        score=distance,
                    )
                )
            output.append(QueryResultSchema(query=query.query, results=inner_results))

        return output

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilterSchema] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Multiple parameters can be used at once.
        Returns whether the operation was successful.
        """
        if delete_all:
            # Dropping the collection removes every vector in it; Chroma rejects an empty delete().
            self._client.delete_collection(self._collection.name)
            return True

        where_clause: Optional[Dict] = None
        if ids and len(ids) > 0:
            if len(ids) > 1:
                where_clause = {"$or": [{"document_id": id_} for id_ in ids]}
            else:
                (id_,) = ids
                where_clause = {"document_id": id_}

            if filter:
                where_clause = {
                    "$and": [
                        self._where_from_query_filter(filter),
                        where_clause,
                    ]
                }
        elif filter:
            where_clause = self._where_from_query_filter(filter)

        self._collection.delete(where=self._normalize_where(where_clause))
        return True
