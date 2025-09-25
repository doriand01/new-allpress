import logging

from allpress.db.connections import DatabaseManager
from allpress.exceptions import ForeignKeyWithoutReference

class DatabaseService:
    """
    functions;
    generate_create_table_query(
        self
        table_name: str
        column_names_and_types: dict
        primary_key=None: str
        foreign_key=None: str
        reference_table=None: str
        reference_column=None: str
        ) -> str
    generate_insertion_query(self
        table_name: str,
        column_names=[]: list:
        values=[]: list
        ) -> str:
    """

    def __init__(self):
        self.db = DatabaseManager()

    def save_model(self, model):
        """Generic save method for any model"""
        data = model.to_dict()
        columns = list(data.keys())
        values = list(data.values())

        query = self._generate_insert_query(model.model_name, columns)
        self.db.cursor.execute(query, values)
        self.db.connection.commit()

    def _generate_insert_query(self, table_name: str, column_names: list) -> str:
        """Generates a safe, parameterized SQL insertion query."""
        placeholders = ', '.join(['%s'] * len(column_names))
        columns = ', '.join(column_names)
        return f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders});'

    def insert_row(self, table: str, column_names: list, values: list):
        insert_query = self._generate_insert_query(table, column_names)
        self.db.cursor.execute(insert_query, values)
        self.db.connection.commit()

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


