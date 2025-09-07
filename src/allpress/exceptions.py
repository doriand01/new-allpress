
class ForeignKeyWithoutReference(Exception):
    """Raised when a foreign key is defined without a reference to another table."""
    def __init__(self, message="Foreign key must reference another table."):
        super().__init__(message)