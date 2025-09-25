from allpress.core.database import DatabaseService
from allpress.services.nlp.processors import (
    sem_embedder,
    rhet_embedder,
    entity_nlp,
    sentence_nlp)
from allpress.services.vectors import VectorDB
from allpress.settings import CLASSIFICATION_MODELS_PATH

from os.path import join

import torch

vector_db = VectorDB()
db_service = DatabaseService()

semantic_autoencoder = torch.load(join(CLASSIFICATION_MODELS_PATH, 'semantic_autoencoder.pth'))
rhet_autoencoder = torch.load(join(CLASSIFICATION_MODELS_PATH, 'rhetoric_autoencoder.pth'))

def _mask_sentences(sentences, entities) -> list[str]:

    for i in range(len(sentences)):
        for entity in entities:
            if entity in sentences[i]:
                sentences[i] = sentences[i].replace(entity, '[MASK]')

    return sentences


class Searcher:

    def __init__(self, top_1_k: int, top_2_k: int):
        self.top_1_k = top_1_k
        self.top_2_k = top_2_k

    def search(self, query: str):
        query_entity_doc = entity_nlp(query)
        query_sentence_doc = sentence_nlp(query)

        query_entities = [ent.text for ent in query_entity_doc.ents]
        query_sentences = _mask_sentences([sent.text for sent in query_sentence_doc.sents], query_entities)

        sem_autoencoded = semantic_autoencoder.encode(
            torch.tensor(sem_embedder.encode(query_entities))
        )

        rhet_autoencoded = rhet_autoencoder.encode(
            torch.tensor(rhet_embedder.encode(query_sentences))
        )

        total_distance_scores_sem = {}
        total_distance_scores_rhet = {}

        for vec in sem_autoencoded:
            distances, indices = vector_db.sem_index.search(
                vec.reshape(1, -1).detach().numpy(),
                self.top_1_k,
            )
            for distance, index in zip(distances[0], indices[0]):
                article_id = db_service.db.redis_cursor.hget('rhetoric', str(index))
                if article_id not in total_distance_scores_sem.keys():
                    total_distance_scores_sem[article_id] = distance
                else:
                    total_distance_scores_sem[article_id] += distance

        for vec in rhet_autoencoded:
            distances, indices = vector_db.rhet_index.search(
                vec.reshape(1, -1).detach().numpy(),
                self.top_1_k,
            )
            for distance, index in zip(distances[0], indices[0]):
                article_id = db_service.db.redis_cursor.hget('rhetoric', str(index))
                if article_id not in total_distance_scores_rhet.keys():
                    total_distance_scores_rhet[article_id] = distance
                else:
                    total_distance_scores_rhet[article_id] += distance

        intersection = set(total_distance_scores_sem.keys()) & set(total_distance_scores_rhet.keys())
        final_results = []
        for article_id in intersection:
            combined = total_distance_scores_sem[article_id] + total_distance_scores_rhet[article_id]
            final_results.append((article_id, combined))
        final_results.sort(key=lambda x: x[1])
        print('hi')





