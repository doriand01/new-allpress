import logging
from typing import NamedTuple, Tuple, List
from numpy import ndarray
from torch import Tensor

URL_PARSE_REGEX = '((http|https):\/\/)?(((www|ww\d|www\d)\.)?(?=.{5,255})([\w-]{2,63}\.)+\w{2,63})(\/[\w\-._~:?#@!$&\'\(\)*+,;%=]+)*\/?'

logging.basicConfig(format='[%(levelname)s];%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                    level=logging.INFO,
                    filename='app.log',
                    filemode='a',
)

logger = logging.getLogger('allpress')

class EmbeddingResult(NamedTuple):
    semantic: List[Tuple[ndarray, str]]
    rhetoric: List[Tuple[Tensor, str]]