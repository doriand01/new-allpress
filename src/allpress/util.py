import logging
from allpress import exceptions

URL_PARSE_REGEX = '((http|https):\/\/)?(((www|ww\d|www\d)\.)?(?=.{5,255})([\w-]{2,63}\.)+\w{2,63})(\/[\w\-._~:?#@!$&\'\(\)*+,;%=]+)*\/?'

logging.basicConfig(format='[%(levelname)s];%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                    level=logging.INFO,
                    filename='app.log',
                    filemode='a',
)

logger = logging.getLogger('allpress')

def check_redis_connection(db_service):
    if not db_service.db.redis_cursor:
        raise exceptions.RedisUnreachable
    else:
        try:
            db_service.db.redis_cursor.ping()
        except Exception as e:
            raise exceptions.RedisUnreachable


def mask_sentences(sentences, entities) -> list[str]:

    for i in range(len(sentences)):
        for entity in entities:
            if entity in sentences[i]:
                sentences[i] = sentences[i].replace(entity, '[MASK]')

    return sentences

class ModuleLogger:

    def __init__(self, level: str='DEBUG', verbose: bool = False):
        self.verbose = verbose
        self.level = level
        logging.basicConfig(format='[%(levelname)s];%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.DEBUG,
                            filename='app.log',
                            filemode='a',
                            )
        self.logger = logging.getLogger('allpress')

    def log(self, message: str, level: str = 'INFO'):
        if self.verbose:
            print(f'[{level}] {message}')
        level = level.lower()
        getattr(self.logger, level)(message)

    def set_verbose(self, verbose: bool):
        self.verbose = verbose


logger = ModuleLogger()