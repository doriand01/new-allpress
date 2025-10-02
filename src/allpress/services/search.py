from allpress.services.db import db_service

from allpress.services.nn import model_manager
from allpress.core.nn import vector_db
from allpress.settings import CLASSIFICATION_MODELS_PATH

from os.path import join

import torch

from allpress.util import mask_sentences

class Searcher:

    def __init__(self, top_1_k: int, top_2_k: int):
        self.top_1_k = top_1_k
        self.top_2_k = top_2_k

    def search(self, query: str):

        with model_manager.get_entity_nlp() as entity_nlp:
            query_entity_doc = entity_nlp(query)

        with model_manager.get_sentence_nlp() as sentence_nlp:
            query_sentence_doc = sentence_nlp(query)

        query_entities = [ent.text for ent in query_entity_doc.ents]
        query_sentences = mask_sentences([sent.text for sent in query_sentence_doc.sents], query_entities)

        with model_manager.get_embedders() as embedders:
            sem_embedder, rhet_embedder = embedders
            with model_manager.get_autoencoders() as autoencoders:
                sem_autoencoder, rhet_autoencoder = autoencoders
                sem_autoencoded = sem_autoencoder.encode(
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





