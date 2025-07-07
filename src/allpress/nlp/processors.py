from bs4 import BeautifulSoup as Soup
from sentence_transformers import SentenceTransformer as Model

import regex
import spacy
import io
import torch
from os import cpu_count

from allpress.db.io import PageModel

from torch import Tensor

torch.set_num_threads(cpu_count())
entity_nlp = spacy.load('xx_ent_wiki_sm')
sentence_nlp = spacy.load('xx_sent_ud_sm')
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
                tokens.append(f'[{token.ent_type_}]')
            else:
                tokens.append(token.text)
        return ' '.join(tokens)

    def _semantic_mask(self):
        masked_doc = ' '.join(self.entities)
        return masked_doc

    def _blobify(self, embedding: Tensor):
        """Converts a PyTorch tensor to a bytes-like object."""
        buffer.seek(0)
        torch.save(embedding, buffer)
        return buffer.getvalue()

    def _split_sentences(self, text):
        """Splits the document text into sentences."""
        sentences = sentence_nlp(text).sents
        return [sentence.text for sentence in sentences]




    def __init__(self,
                 url: str,
                 content: Soup):

        self.url = url
        self.html = content
        self.raw_text = self._extract_text()
        self.document = entity_nlp(self.raw_text)
        self.doc_text = self.document.text
        self.entities = [ent.text for ent in self.document.ents]
        self.entity_string = ' '.join(self.entities)
        self.rhetoric = self._rhetorical_mask()
        self.sentences = self._split_sentences(self.rhetoric)
        self.semantic = self._semantic_mask()

        sentence_embeddings = embedder.encode(self.sentences, convert_to_tensor=True, show_progress_bar=False)
        self.rhetorical_embedding = None

        # Initialize semantic embedding to None
        self.semantic_embedding = None

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

    def __init__(self, articles: list[Article]):
        super().__init__(articles)

    def serialize(self):
        return [article.serialize() for article in self]

    def embed_rhetorical(self, device='cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Efficiently computes rhetorical embeddings for all articles in the batch.
        Sentences from all articles are embedded in a single batch for speed.
        """
        embedder.to(device)

        all_sentences = []
        sentence_counts = []

        # 1. Collect and store all sentences
        for article in self:
            sentences = article._split_sentences(article.rhetoric)
            article._rhetorical_sentences = sentences  # store temporarily
            all_sentences.extend(sentences)
            sentence_counts.append(len(sentences))

        if not all_sentences:
            print("No rhetorical sentences found. Skipping embedding.")
            return

        # 2. Batch-encode all sentences
        sentence_embeddings = embedder.encode(
            all_sentences,
            convert_to_tensor=False,
            normalize_embeddings=True,
            show_progress_bar=True,
            device=device,
        )

        # 3. Assign mean-pooled rhetorical vectors back to each article
        idx = 0
        for article, count in zip(self, sentence_counts):
            if count == 0:
                article.rhetorical_embedding = None
                continue
            sentence_slice = sentence_embeddings[idx:idx + count]
            pooled = torch.mean(sentence_slice, dim=0, keepdim=True)
            article.rhetorical_embedding = article._blobify(pooled)
            idx += count

        print("Finished embedding rhetorical vectors.")

    def generate_embeddings(self):
        all_semantic = [article.semantic for article in self]

        semantic_embeddings = embedder.encode(all_semantic, convert_to_tensor=True, show_progress_bar=False)
        self.embed_rhetorical()

        for i, article in enumerate(self):
            article.semantic_embedding = article._blobify(semantic_embeddings[i])

