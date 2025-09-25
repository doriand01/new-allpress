
class ForeignKeyWithoutReference(Exception):
    """Raised when a foreign key is defined without a reference to another table."""
    def __init__(self, message="Foreign key must reference another table."):
        super().__init__(message)

class RedisUnreachable(Exception):
    """Raised when a Redis connection is unreachable."""

    def __init__(self, message="Redis connection is unreachable."):
        super().__init__(message)


class SQLDatabaseUnreachable(Exception):
    """Raised when a SQL database is unreachable."""

    def __init__(self, message="SQL database is unreachable."):
        super().__init__(message)