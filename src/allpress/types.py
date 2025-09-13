from typing import NamedTuple, Tuple, List
from numpy import ndarray
from torch import Tensor

class EmbeddingResult(NamedTuple):
    semantic: List[Tuple[ndarray, str]]
    rhetoric: List[Tuple[Tensor, str]]