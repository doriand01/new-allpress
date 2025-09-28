from hashlib import md5

from allpress.services.db import db_service


class BaseModel:

    def __init__(self, **columns):
        for name, value in zip(columns.keys(), columns.values()):
            setattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{name}', value)

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, val):
        return getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{val}')

    def to_dict(self):
        return {k: getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{k}')
                for k in self.__class__.column_names}

    def verify_primary_key(self, pk_column_name):
        primary_key_column = None
        primary_key_value = None
        table_name = self.__class__.__name__.lower().replace("model", "")
        primary_key_select = f'SELECT {primary_key_column} FROM {table_name} WHERE {primary_key_column} = {primary_key_value}'
        for k, v in self.to_dict().items():
            if "PRIMARY" in v:
                primary_key_column = k
                primary_key_value = getattr(self, pk_column_name)
                db_service.db.cursor.execute(primary_key_select)
                primary_key = db_service.db.cursor.fetchone()


    def save(self):
        """Saves the current instance to the database."""
        # This method should be implemented in subclasses to handle saving logic.
        cls = self.__class__
        serializable = self.to_dict()
        columns = list(serializable.keys())
        data = list(serializable.values())
        db_service.insert_row(cls.model_name, columns, data)


class PageModel(BaseModel):
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
        'url': 'VARCHAR(1024)',
        'text': 'TEXT',
        'uid': 'VARCHAR(32) PRIMARY KEY',  # Unique identifier for the page
    }
    column_names = [
        'url',
        'text',
        'uid',  # Unique identifier for the page
    ]

    def __init__(self, **columns):
        super().__init__(**columns)

        # Creates MD5 hash object to generate a unique UUID for the Page object.
        # MD5 has a low chance of collisions. Perhaps use a different algorithm in the future?
        hashobj = md5()
        hashobj.update(bytes(str(self.page_text).encode('utf-8')))
        uid = hashobj.hexdigest()
        self.page_uid = uid

    def __str__(self):
        return f'<{self.url}...>'

    def save(self):
        """Saves the current instance to the database."""
        if self.verify_primary_key('uid'):
            super().save()

    def to_dict(self):
        """Generates a dictionary representation of the current instance of the
        PageModel class. A dictionary generator is used to find all attributes of the instance
        contained within the specified `column_names` store."""

        return {k: getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{k}')
                for k in self.__class__.column_names}


class NewsSourceModel(BaseModel):
    """
    NewsSourceModel: is the class which models the `news_source` table in the MariaDB database.
    The `news_source` model contains columns which encapsulate the following data relating to
    each indexed news source: its url, and the name of the news source.
    It is a child class of the Model class. All Model classes and child classes
    have no publicly accessible functions, only attributes which help Model a row in
    the database table.
    """
    model_name = 'newssource'

    column_name_type_store = {
        'name': 'VARCHAR(128)',
        'url': 'VARCHAR(1024) UNIQUE',  # URL of the news source
    }
    column_names = [
        'name',
        'url',
    ]

    def __init__(self, **columns):
        # The columns kwarg is a dictionary that contains the row and value for that row
        # for each record in the DB. It is passed to the Model superclass for instantiation.
        super().__init__(**columns)

    def __str__(self):
        return f'<{self.url}...>'

    def to_dict(self):
        """Generates a dictionary representation of the current instance of the
        NewsSourceModel class. A dictionary generator is used to find all attributes"""
        return {k: getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{k}')
                for k in self.__class__.column_names}
