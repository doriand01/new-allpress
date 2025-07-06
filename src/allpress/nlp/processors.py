from bs4 import BeautifulSoup as Soup
from sentence_transformers import SentenceTransformer as Model

import regex
import spacy
import io
import torch

from allpress.db.io import PageModel

from torch import Tensor


nlprocessor = spacy.load('xx_ent_wiki_sm')
embedder = Model('paraphrase-multilingual-MiniLM-L12-v2')
buffer = io.BytesIO()




class Article:

    def _extract_text(self):
        paragraphs = self.html.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        return text.strip()

    def _rhetorical_mask(self):
        tokens = []
        for token in self.document:
            if token.ent_type_:
                tokens.append(' UNK ')
            else:
                tokens.append(token.text_with_ws)
        return ''.join(tokens)

    def _semantic_mask(self):
        masked_doc = ' '.join(self.entities)
        return masked_doc

    def _blobify(self, embedding: Tensor):
        """Converts a PyTorch tensor to a bytes-like object."""
        buffer.seek(0)
        torch.save(embedding, buffer)
        return buffer.getvalue()




    def __init__(self,
                 url: str,
                 content: Soup):

        self.url = url
        self.html = content
        self.document = nlprocessor(self._extract_text())
        self.doc_text = self.document.text
        self.entities = [ent.text for ent in self.document.ents]
        self.entity_string = ' '.join(self.entities)
        self.rhetoric = self._rhetorical_mask()
        self.semantic = self._semantic_mask()
        self.rhetorical_embedding = self._blobify(embedder.encode(self.rhetoric, convert_to_tensor=True))
        self.semantic_embedding = self._blobify(embedder.encode(self.semantic, convert_to_tensor=True))

    def serialize(self):
        article_dict = {
            'url': self.url,
            'text': self.doc_text,
            'rhet_vec': self.rhetorical_embedding,
            'sem_vec': self.semantic_embedding
        }

        return PageModel(**article_dict)


class ArticleBatch(list):
    """
    ArticleBatch: A list subclass that represents a batch of articles.
    It provides a method to serialize the articles in the batch.
    """

    def __init__(self, articles: list[Article], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.articles = articles

    def serialize(self):
        return [article.serialize() for article in self]

