from django.apps import AppConfig
from django.db.backends.signals import connection_created


class WarehouseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.warehouse"

    def ready(self):
        connection_created.connect(
            self._configure_sqlite_connection, dispatch_uid="warehouse.sqlite.pragmas"
        )

    @staticmethod
    def _configure_sqlite_connection(sender, connection, **kwargs):
        if connection.vendor != "sqlite":
            return

        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA wal_autocheckpoint=1000;")
            cursor.execute("PRAGMA busy_timeout=5000;")
