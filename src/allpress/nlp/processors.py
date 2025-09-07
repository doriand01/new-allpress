from bs4 import BeautifulSoup as Soup
from sentence_transformers import SentenceTransformer as Model

import regex
import spacy
import io
import torch
import torch_directml
import numpy as np
from os import cpu_count, path
from hashlib import md5
import sys

from allpress.db.io import PageModel
from allpress.settings import TEMP_TRAINING_VECTOR_PATH

from torch import Tensor

device = torch_directml.device()

torch.set_num_threads(cpu_count())
entity_nlp = spacy.load('xx_ent_wiki_sm')
sentence_nlp = spacy.load('xx_sent_ud_sm')
embedder = Model('paraphrase-multilingual-MiniLM-L12-v2')
sem_embedder = Model('LaBSE')


def print_progress(current, total, label, bar_len=40):
    progress = int(bar_len * (current / total))
    bar = "█" * progress + "░" * (bar_len - progress)
    percent = (current / total) * 100
    sys.stdout.write(f"\r{label}: {current}/{total} [{bar}] {percent:5.1f}%")
    sys.stdout.flush()
    if current == total:
        print()


class Article:

    def _extract_text(self):
        paragraphs = self.html.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        return text.strip()

    def _blobify(self, embedding: Tensor):
        """Converts a PyTorch tensor to a bytes-like object."""
        buffer = io.BytesIO()
        torch.save(embedding, buffer)
        return buffer.getvalue()

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
        self.document = entity_nlp(self.raw_text)
        self.doc_text = self.document.text
        self.entities = [ent.text for ent in self.document.ents]
        self.sentences = self._split_sentences(self.raw_text)
        self.entity_string = ' '.join(self.entities)
        self.masked_rhetoric = self._mask_rhetoric_chunks()
        hashobj = md5()
        hashobj.update(bytes(str(self.doc_text).encode('utf-8')))
        self.id = hashobj.hexdigest()

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
        rhetoric_path = path.join(TEMP_TRAINING_VECTOR_PATH, 'rhetoric.pth')

        # Flatten all masked rhetoric sentences from all articles
        sentences = []
        for article in self:
            for sentence in article.masked_rhetoric:
                sentences.append((str(sentence), article.id))
        sentences = [str(sentence) for article in self for sentence in article.masked_rhetoric]
        total = len(sentences)
        i = 0

        if not path.exists(rhetoric_path):
            embeddings.append(embedder.encode(sentences, convert_to_tensor=True, show_progress_bar=True))
            if not return_embedding:
                torch.save(torch.stack(embeddings), rhetoric_path)
            else:
                return embeddings
        else:
            prev_embeddings = torch.load(rhetoric_path)
            for sentence in sentences:
                embeddings.append(embedder.encode(sentence, convert_to_tensor=True, show_progress_bar=False))
                i += 1
                print_progress(i, total, "Embedding rhetorical sentences")
            concatenated_tensor = torch.cat((torch.stack(embeddings), prev_embeddings), dim=0)
            torch.save(concatenated_tensor, rhetoric_path)


    # Add option to enable or disable return_embedding. Set to true for testing.
    def embed_semantic(self, return_embedding=True):
        embeddings = []
        semantic_path = path.join(TEMP_TRAINING_VECTOR_PATH, 'semantic.pth')

        # Flatten all entities from all articles
        entities = []
        for article in self:
            entities = entities + [(entity, article.id) for entity in article.entities]
        # Eliminate duplicates by wrapping the entities list in a set, then converting it back to a list.
        entities = list(set(entities))
        total = len(entities)
        i = 0

        if not path.exists(semantic_path) or return_embedding:
            only_entity_strings = [entity[0] for entity in entities]
            # entity[0] is the embedding itself, entity[1] is the article id.
            embeddings.append((sem_embedder.encode(only_entity_strings, convert_to_tensor=False, show_progress_bar=True), [entity[1] for entity in entities]))
            print_progress(i, total, "Embedding semantic entities")
            if not return_embedding:
                torch.save(torch.stack(embeddings), semantic_path)
            else:
                return embeddings
        else:
            prev_embeddings = torch.load(semantic_path)
            for entity in entities:
                with torch.inference_mode():
                    embeddings.append(sem_embedder.encode(entity, convert_to_tensor=False, show_progress_bar=False))
                    i += 1
                    print_progress(i, total, "Embedding semantic entities")
            concatenated_tensor = torch.cat((torch.stack(embeddings), prev_embeddings), dim=0)
            torch.save(concatenated_tensor, semantic_path)


    def generate_embeddings(self):

        return self.embed_semantic(), self.embed_rhetorical()


