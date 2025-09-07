import mariadb
import faiss
import redis

from hashlib import md5
from allpress.settings import (
    DATABASE_USERNAME,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_NAME,
    FAISS_INDEX_PATH
)
from allpress.util import logging
from torch.utils.data import Dataset


from allpress.exceptions import *

import numpy as np

conn_params = {
    'user': DATABASE_USERNAME,
    'password': DATABASE_PASSWORD,
    'host': DATABASE_HOST,
    'database': DATABASE_NAME
}

connection = mariadb.connect(**conn_params)
cursor = connection.cursor()

redis_cursor = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

class Transactions:
    """
    Transactions: Helper class to assist in interactions with PostgreSQL \n
    database. Only contains functions and is not an object on its own.\n
    \n
    functions;\n
    generate_create_table_query(\n
        self \n
        table_name: str \n
        column_names_and_types: dict \n
        primary_key=None: str \n
        foreign_key=None: str \n
        reference_table=None: str \n
        reference_column=None: str \n
        ) -> str\n
    generate_insertion_query(self \n
        table_name: str, \n
        column_names=[]: list: \n
        values=[]: list \n
        ) -> str:\n
    move_east(self, value: float, in_='miles')\n
    move_west(self, value: float, in_='miles')\n
    move_north(self, value: float, in_='miles')\n
    move_south(self, value: float, in_='miles')\n
    clone(self)\n
    """

    @classmethod
    def generate_create_table_query(self,
                                    table_name: str,
                                    column_names_and_types: dict,
                                    primary_key=None,
                                    foreign_key=None,
                                    reference_table=None,
                                    reference_column=None) -> str:
        """Generates a query to create a new table in the database. \n\n
        table name: str (Name of table to be created) \n
        column_names_and_types: dict (Key-value dictionary containing
        tha name of every column and the column's datatype. Refer to
        allpress.db.models.Model classes.) \n
        **primary_key: str (Sets primary key in table. Optional argument.) \n
        **foreign_key: str (Sets foreign keys in table. Optional argument.) \n
        **reference_table: (Sets reference table for foreign key. Optional
        argument, but required when foreign_key is used, or will raise
        ForeignKeyWithoutReferenceError.)
        """
        column_names_and_types_string = ''
        for key, val in zip(list(column_names_and_types.keys()), list(column_names_and_types.values())):
            if primary_key and key == primary_key:
                column_names_and_types_string += f'{key} {val} PRIMARY KEY,'
                continue

            if (foreign_key and reference_table) and (key == foreign_key):
                if reference_column:
                    column_names_and_types_string += f'{key} {val} REFERENCES {reference_table}({reference_column}),'
                else:
                    column_names_and_types_string += f'{key} {val} REFERENCES {reference_table}({foreign_key}),'
                continue
            elif foreign_key and not reference_table:
                logging.critical(f'Reference table not provided for foreign key {foreign_key}! Abort.')
                raise ForeignKeyWithoutReference(f'Reference table not provided for foreign key {foreign_key}')
            column_names_and_types_string += f'{key} {val},'

        return f'CREATE TABLE {table_name} ({column_names_and_types_string[:-1]})'

    @staticmethod
    def generate_insertion_query(table_name: str, column_names: list) -> str:
        """Generates a safe, parameterized SQL insertion query."""
        placeholders = ', '.join(['%s'] * len(column_names))
        columns = ', '.join(column_names)
        return f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders});'

    @staticmethod
    def insert_row(table: str, column_names: list, values: list):
        insert_query = Transactions.generate_insertion_query(table, column_names)
        cursor.execute(insert_query, values)
        connection.commit()


class Model:

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

    def save(self):
        """Saves the current instance to the database."""
        # This method should be implemented in subclasses to handle saving logic.
        cls = self.__class__
        serializable = self.to_dict()
        columns = list(serializable.keys())
        data = list(serializable.values())
        Transactions.insert_row(cls.model_name, columns, data)



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
        hashobj = md5()
        hashobj.update(bytes(str(self.page_text).encode('utf-8')))
        uid = hashobj.hexdigest()
        self.page_uid = uid

    def __str__(self):
        return f'<{self.url}...>'

    def to_dict(self):
        """Generates a dictionary representation of the current instance of the
        PageModel class. A dictionary generator is used to find all attributes of the instance
        contained within the specified `column_names` store."""

        return {k: getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{k}')
                for k in self.__class__.column_names}


class NewsSourceModel(Model):
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
        super().__init__(**columns)

    def __str__(self):
        return f'<{self.url}...>'

    def to_dict(self):
        return {k: getattr(self, f'{self.__class__.__name__.lower().replace("model", "")}_{k}')
                for k in self.__class__.column_names}

class VectorDB:

    def __init__(self):
        self.rhet_index = faiss.IndexFlatL2(256)
        self.sem_index = faiss.IndexFlatL2(256)


    def _md5_to_uid(self, hash):
        faiss_id = int(f'0x{hash[:15]}', 16)
        redis_cursor.set(str(faiss_id), hash)
        return faiss_id

    def insert_vectors(self, embeddings):

        for embedding in embeddings:
            pass
            faiss.write_index(self.rhet_index, FAISS_INDEX_PATH.replace('.faiss', '_rhetoric.faiss'))
            faiss.write_index(self.sem_index, FAISS_INDEX_PATH.replace('.faiss', '_semantic.faiss'))


class VectorDataset(Dataset):
    class VectorDataset(Dataset):
        def __init__(self, data_tensor):
            self.data = data_tensor

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            return self.data[idx]



