


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
            query = Transactions.generate_create_table_query(
                table_name=PageModel.model_name,
                column_names_and_types=PageModel.column_name_type_store,
            )
            cursor.execute(query)

            connection.commit()