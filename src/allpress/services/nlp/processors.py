from bs4 import BeautifulSoup as Soup
from sentence_transformers import SentenceTransformer as Model

import spacy
import torch
import torch_directml
from os import cpu_count, path
from hashlib import md5

from allpress.core.models import PageModel
from allpress.types import EmbeddingResult
from allpress.services.nn import model_manager


device = torch_directml.device()

torch.set_num_threads(cpu_count())
sentence_nlp = spacy.load('xx_sent_ud_sm')
rhet_embedder = Model('paraphrase-multilingual-MiniLM-L12-v2')
sem_embedder = Model('LaBSE')

class Article:

    def _extract_text(self):
        paragraphs = self.html.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        return text.strip()

    def _split_sentences(self, text):
        """Splits the document text into sentences."""
        sentences = sentence_nlp(text).sents
        return [sentence for sentence in sentences]

    def _mask_rhetoric_chunks(self) -> list[str]:

        masked_sentences = []

        for i in range(len(self.sentences)):
            masked_sentences.append([])
            for token in self.sentences[i]:
                if token.ent_type_:
                    masked_sentences[i].append("[MASK]")
                else:
                    masked_sentences[i].append(token.text)
            masked_sentences[i] = ' '.join(masked_sentences[i])
        return masked_sentences





    def __init__(self,
                 url: str,
                 content: Soup):

        self.url = url
        self.html = content
        self.raw_text = self._extract_text()
        with model_manager.get_entity_nlp() as entity_nlp:
            self.document = entity_nlp(self.raw_text)
            self.doc_text = self.document.text
            self.entities = [ent.text for ent in self.document.ents]
        self.sentences = self._split_sentences(self.raw_text)
        self.masked_rhetoric = self._mask_rhetoric_chunks()
        hashobj = md5()
        hashobj.update(bytes(str(self.doc_text).encode('utf-8')))
        self.id = hashobj.hexdigest()
        del hashobj

        self.rhetorical_embedding = None

        # Initialize semantic embedding to None
        self.semantic_embedding = None

    def serialize(self):
        article_dict = {
            'url': self.url,
            'text': self.doc_text,
        }

        return PageModel(**article_dict)


class ArticleBatch(list):
    """
    ArticleBatch: A list subclass that represents a batch of articles.
    It provides a method to serialize the articles in the batch.
    """

    def __init__(self, articles: list[Article]):
        super().__init__(articles)

    def serialize(self):
        """Returns a serializable PageModel object for each article.
        These PageModel objects can be saved directly to the database
        using the `save()` method."""
        return [article.serialize() for article in self]

    def embed_rhetorical(self, return_embedding=True):
        embeddings = []

        # Flatten all masked rhetoric sentences from all articles
        sentences = []
        with model_manager.get_embedders(embedder='rhetoric') as rhet_embedder:
            for article in self:
                for sentence in article.masked_rhetoric:
                    # Appends a tuple containing two objects: A string representation of the sentence to be embedded,
                    # and the UUID of the article it came from.
                    sentences.append((str(sentence), article.id))

            only_sentences = [sentence[0] for sentence in sentences]
            article_ids = [sentence[1] for sentence in sentences]
            embeddings.append(
                (rhet_embedder.encode(only_sentences, convert_to_tensor=False, show_progress_bar=False), article_ids)
            )
            return embeddings


    # Add option to enable or disable return_embedding. Set to true for testing.
    def embed_semantic(self, return_embedding=True):
        embeddings = []
        # Flatten all entities from all articles
        entities = []

        with model_manager.get_embedders(embedder='semantic') as sem_embedder:
            for article in self:
                # Generates a tuple that contains two objects; a string representation of the entity, and the UUID of the
                # article it came from.
                entities = entities + [(entity, article.id) for entity in article.entities]

            total = len(entities)
            i = 0

            # Make a list only containing the entity strings for embedding.
            only_entity_strings = [entity[0] for entity in entities]
            article_ids = [entity[1] for entity in entities]

            # entity[0] is the embedding itself, entity[1] is the article id.
            embeddings.append(
                (sem_embedder.encode(only_entity_strings, convert_to_tensor=False, show_progress_bar=False), article_ids)
            )
            return embeddings


    def generate_embeddings(self):
        semantic = self.embed_semantic()
        rhetoric = self.embed_rhetorical()
        return EmbeddingResult(semantic=semantic, rhetoric=rhetoric)


