import mariadb
import redis

from allpress.settings import (
    DATABASE_USERNAME,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_NAME,
)


class DatabaseManager:
    _instance = None
    _connection = None
    _cursor = None
    _redis = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def connection(self):
        if self._connection is None:
            conn_params = {
                'user': DATABASE_USERNAME,
                'password': DATABASE_PASSWORD,
                'host': DATABASE_HOST,
                'database': DATABASE_NAME
            }
            self._connection = mariadb.connect(**conn_params)
        return self._connection

    @property
    def cursor(self):
        if self._cursor is None:
            self._cursor = self.connection.cursor()
        return self._cursor

    @property
    def redis_cursor(self):
        if self._redis is None:
            self._redis = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
        return self._redis