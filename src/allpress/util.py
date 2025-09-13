import logging


URL_PARSE_REGEX = '((http|https):\/\/)?(((www|ww\d|www\d)\.)?(?=.{5,255})([\w-]{2,63}\.)+\w{2,63})(\/[\w\-._~:?#@!$&\'\(\)*+,;%=]+)*\/?'

logging.basicConfig(format='[%(levelname)s];%(asctime)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                    level=logging.INFO,
                    filename='app.log',
                    filemode='a',
)

logger = logging.getLogger('allpress')

