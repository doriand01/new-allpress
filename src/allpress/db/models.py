from hashlib import md5

class Model:

    def __init__(self, **columns):
        for name, value in zip(columns.keys(), columns.values()):
            setattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{name}', value)

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, val):
        return getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{val}')


class PageModel(Model):
    """
    PageModel: is the class which models the `page` table in the MariaDB database. \n
    The page model contains columns which encapsulate the following data relating to \n
    each indexed page: its url, the root url of the website, the `<p>` tag data \n
    contained within the table, the language of the page, and translations for that \n
    page. It is a child class of the Model class. All Model classes and child classes\n
    have no publicly accessible functions, only attributes which help Model a row in \n
    the database table.
    \n
    """
    model_name = 'page'

    column_name_type_store = {
        'url'          : 'varchar(2048)',
        'home_url'     : 'varchar(2048)',
        'p_data'       : 'text',
        'news_source'  : 'varchar(128)',
        'title'        : 'text',
        'date'         : 'text'
    }
    column_names = [
        'url', 'home_url',
        'p_data',
        'news_source',
        'title', 'date'
    ]
    def __init__(self, **columns):
        super().__init__(**columns)
        hashobj = md5()
        hashobj.update(bytes(str(self.p_data).encode('utf-8')))
        uid = hashobj.hexdigest()
        self.page_uid = uid

    def __str__(self):
        return f'<{self.page_url}...>'

    def to_dict(self):
        return {k: getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{k}')
                for k in self.__class__.column_names}