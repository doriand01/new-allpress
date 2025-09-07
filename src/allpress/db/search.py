import faiss
import numpy as np
from allpress.settings import FAISS_INDEX_PATH


class FAISS_DB:

    def __init__(self):
        self.index = None
        self.is_initialized = False

    def initialize(self, dimension: int):
        """
        Initialize the FAISS index with the given dimension.

        :param dimension: The dimensionality of the vectors to be indexed.
        """
        self.index = faiss.IndexFlatL2(dimension)
        self.is_initialized = True
        print(f"FAISS index initialized with dimension {dimension}.")

    def add_vectors(self, vectors: list[np.ndarray], ids: list[int]):
        if len(vectors) != len(ids):
            raise ValueError("Number of vectors must match number of IDs.")
