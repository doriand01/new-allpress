from allpress.settings import (
    DATABASE_USERNAME,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_NAME,
    NEWS_SOURCE_CATALOG_FILE,
    CONFIG_FILE_PATH,
)

from allpress.services.db import db_service
from allpress.core.models import PageModel, NewsSourceModel

import os

configurations = {
    'is_initialized': True,
    'application_tables': [
        'page',
        'sources',
    ]
}


def load_sources_from_csv():
    """
    Load news sources from a CSV file and insert them into the database.

    :param file_path: Path to the CSV file containing news sources.
    """
    import csv

    if os.stat(NEWS_SOURCE_CATALOG_FILE).st_size == 0:
        print(f"CSV file {NEWS_SOURCE_CATALOG_FILE} does not exist.")
        return

    with open(NEWS_SOURCE_CATALOG_FILE, mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            info = {
                'name': row[2],
                'url': row[4],
            }
            # The magic numbers presuppose CSV file structure. This should be fixed later.

            source = NewsSourceModel(**info)
            db_service.insert_row('newssource', source.column_names, list(info.values()))


class DBSetup:

    @staticmethod
    def _check_table_exists(table_name: str, db_name: str = DATABASE_NAME) -> bool:
        """
        Check if a table exists in the database.

        :param table_name: Name of the table to check.
        :param db_name: Name of the database to check in.
        :return: True if the table exists, False otherwise.
        """
        db_service.db.cursor.execute(f"""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = '{db_name}' AND table_name = '{table_name}'
        ) AS table_exists
        """)

        result = db_service.db.cursor.fetchone()[0]
        return result == 1
    @staticmethod
    def setup_application_tables():
        # Sets up the tables required for use by the application.
        # First checks if the tables exist, and if not, creates then.
        if not DBSetup._check_table_exists('page'):
            query = db_service.generate_create_table_query(
                table_name=PageModel.model_name,
                column_names_and_types=PageModel.column_name_type_store,
            )
            db_service.db.cursor.execute(query)

            db_service.db.connection.commit()

        if not DBSetup._check_table_exists('newssource'):
            query = db_service.generate_create_table_query(
                table_name=NewsSourceModel.model_name,
                column_names_and_types=NewsSourceModel.column_name_type_store,
            )
            db_service.db.cursor.execute(query)

            db_service.db.connection.commit()

            print('Loading sources from CSV file if available.')
            load_sources_from_csv()


def check_config():

    if os.stat(CONFIG_FILE_PATH).st_size == 0:
        print("Config file is empty. Initializing application...")
        DBSetup.setup_application_tables()
        print("A minimum of 1000 articles are required to train autoencoders for classification. Please add at least 1000 articles to the database before training.")
        with open('config.json', 'w') as config_file:
            import json
            json.dump(configurations, config_file, indent=4)


