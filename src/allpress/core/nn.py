from os import path

import faiss
from torch import Tensor

from allpress.services.db import db_service
from allpress.settings import FAISS_INDEX_PATH


class VectorDB:

    def __init__(self):
        # VectorDB is an interface to write autoencoded vectors to disk for later retrieval.
        # The file paths to the semantic and rhetorical db, as well as the faiss databases themselves
        # (read from disk or created on the spot if it does not exist) are instance attributes.
        self.semantic_vectordb_path = path.join(FAISS_INDEX_PATH, 'index_semantic.faiss')
        self.rhetoric_vectordb_path = path.join(FAISS_INDEX_PATH, 'index_rhetoric.faiss')

        # Loads the faiss vectordb from disk if it exists. Else, it makes a new empty one.
        self.sem_index = faiss.read_index(self.semantic_vectordb_path) if path.exists(self.semantic_vectordb_path) else faiss.IndexFlatL2(128)
        self.rhet_index = faiss.read_index(self.rhetoric_vectordb_path) if path.exists(self.rhetoric_vectordb_path) else faiss.IndexFlatL2(256)


    def insert_vectors(self, embeddings: Tensor, ids: list, write_to=None):

        # write_to specifies whether the function is to serialize to the vector db holding the semantic vectors or
        # rhetorical vectors.

        # Size of the current faiss db, so the writer knows where to begin counting for mapping vector db indexes
        # to individual article IDs in redis.
        current_index_size = self.sem_index.ntotal \
            if write_to == 'semantic' \
            else self.rhet_index.ntotal \
            if write_to == 'rhetoric' \
            else None
        new_vec_ids = [i + current_index_size for i in range(len(embeddings))]

        # Map the vector ids to articles in redis, add new embeddings, and write updated faiss db to disk.
        if write_to == 'semantic':
            for i in range(len(new_vec_ids)):
                db_service.db.redis_cursor.hset(name='semantic', key=str(new_vec_ids[i]), value=ids[i])
            self.sem_index.add(embeddings)
            faiss.write_index(self.sem_index, self.semantic_vectordb_path)
        elif write_to == 'rhetoric':
            for i in range(len(new_vec_ids)):
                db_service.db.redis_cursor.hset(name='rhetoric', key=str(new_vec_ids[i]), value=ids[i])
            self.rhet_index.add(embeddings)
            faiss.write_index(self.rhet_index, self.rhetoric_vectordb_path)
        else:
            # Add code for error handling here later
            pass
