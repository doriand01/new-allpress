import mariadb

from allpress.settings import (
    DATABASE_USERNAME,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_NAME
)

from allpress.exceptions import *
from allpress.db.models import Model, PageModel

conn_params = {
    'user': DATABASE_USERNAME,
    'password': DATABASE_PASSWORD,
    'host': DATABASE_HOST,
    'database': DATABASE_NAME
}

connection = mariadb.connect(**conn_params)
cursor = connection.cursor()


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
                raise ForeignKeyWithoutReferenceError(f'Reference table not provided for foreign key {foreign_key}')
            column_names_and_types_string += f'{key} {val},'

        return f'CREATE TABLE {table_name} ({column_names_and_types_string[:-1]})'

class DBSetup:

    @staticmethod
    def _check_table_exists(table_name: str, db_name: str = DATABASE_NAME) -> bool:
        """
        Check if a table exists in the database.

        :param table_name: Name of the table to check.
        :param db_name: Name of the database to check in.
        :return: True if the table exists, False otherwise.
        """
        cursor.execute(f"""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = {db_name} AND table_name = {table_name}
        ) AS table_exists
        """)

        result = cursor.fetchone()[0]
        return result == 1
    @staticmethod
    def setup_application_tables():
        # Sets up the tables required for use by the application.
        # First checks if the tables exist, and if not, creates then.
        if not DBSetup._check_table_exists('page'):
            cursor.execute(Transactions.generate_create_table_query(
                    table_name=PageModel.model_name,
                    column_names_and_types=PageModel.column_name_type_store,
                )
            )

            connection.commit()


