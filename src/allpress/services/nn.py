import gc
import torch
from contextlib import contextmanager
from typing import Optional
from os.path import join

from allpress.settings import CLASSIFICATION_MODELS_PATH

semantic_autoencoder_path = join(CLASSIFICATION_MODELS_PATH, 'semantic_autoencoder.pth')
rhetoric_autoencoder_path = join(CLASSIFICATION_MODELS_PATH, 'rhetoric_autoencoder.pth')


class ModelManager:
    def __init__(self):
        self._entity_nlp: Optional = None
        self._sentence_nlp: Optional = None
        self._semantic_embedder: Optional = None
        self._rhetoric_embedder: Optional = None
        self._semantic_autoencoder: Optional = None
        self._rhetoric_autoencoder: Optional = None

    @contextmanager
    def get_entity_nlp(self):
        """Load model only when needed, cleanup after use"""
        if self._entity_nlp is None:
            import spacy
            self._entity_nlp = spacy.load('xx_ent_wiki_sm')

        try:
            yield self._entity_nlp
        finally:
            # Optionally unload if memory is tight
            if self.should_unload_models():
                self._entity_nlp = None
                gc.collect()

    @contextmanager
    def get_sentence_nlp(self):
        """Load model only when needed, cleanup after use"""
        if self._sentence_nlp is None:
            import spacy
            self._sentence_nlp = spacy.load('xx_sent_ud_sm')
        try:
            yield self._sentence_nlp
        finally:
            gc.collect()

    @contextmanager
    def get_embedders(self, embedder: str=''):

        """Load both embedders together ince they're often used together"""
        if self._semantic_embedder is None and (not embedder or embedder == 'semantic'):
            from sentence_transformers import SentenceTransformer
            self._semantic_embedder = SentenceTransformer('LaBSE')

        if self._rhetoric_embedder is None and (not embedder or embedder == 'rhetoric'):
            from sentence_transformers import SentenceTransformer
            self._rhetoric_embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        try:
            if not embedder:
                yield self._semantic_embedder, self._rhetoric_embedder
            elif embedder == 'semantic':
                yield self._semantic_embedder
            elif embedder == 'rhetoric':
                yield self._rhetoric_embedder
        finally:
            # Keep embedders loaded since they're frequently used
            pass

    @contextmanager
    def get_autoencoders(self):
        """Load autoencoders only for search operations"""
        if self._semantic_autoencoder is None:
            self._semantic_autoencoder = torch.load(
                semantic_autoencoder_path,
                map_location='cpu',  # Force CPU to save GPU memory
                weights_only=False
            )

        if self._rhetoric_autoencoder is None:
            self._rhetoric_autoencoder = torch.load(
                rhetoric_autoencoder_path,
                map_location='cpu',
                weights_only=False
            )

        try:
            yield self._semantic_autoencoder, self._rhetoric_autoencoder
        finally:
            # Keep autoencoders loaded for search operations
            pass

    def should_unload_models(self) -> bool:
        """Check if we should unload models based on memory usage"""
        import psutil
        memory_percent = psutil.virtual_memory().percent
        return memory_percent > 80  # Unload if using more than 80% RAM

    def clear_all_models(self):
        """Force cleanup of all models"""
        self._entity_nlp = None
        self._sentence_nlp = None
        self._semantic_embedder = None
        self._rhetoric_embedder = None
        self._semantic_autoencoder = None
        self._rhetoric_autoencoder = None
        gc.collect()

model_manager = ModelManager()