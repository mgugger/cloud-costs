import os
import logging
from peewee import MySQLDatabase, Proxy
from playhouse.sqlite_ext import SqliteExtDatabase
from src.constants import Constants

class RecordCounter:
    _instance = None
    _count = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def count(self):
        self._count += 1
        return self._count

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.record_number = RecordCounter().count()
        return True

class Borg:
    _shared_state = {}
    def __init__(self):
        self.__dict__ = self._shared_state

class Settings(Borg):
    def __init__(self):
        Borg.__init__(self)
        if not hasattr(self, 'db'):
            self.db = Proxy()

        if not hasattr(self, 'db_logger'):
            self.db_logger = logging.getLogger('peewee')
            self.db_logger.setLevel(logging.DEBUG)
            self.db_logger.addFilter(ContextFilter())

            # PEEWEE: Log Queries
            #if os.getenv('DEBUG') == 'True':
            #    self.db_logger.addHandler(logging.StreamHandler())


    def init_db(self):
        if os.getenv('USE_IN_MEMORY_DB') == 'True':
            print("Running with In-Memory Backend")
            self.db.initialize(SqliteExtDatabase(':memory:', regexp_function=True))
        elif os.getenv('USE_MYSQL') == 'True':
            print("Running with Mysql Backend")
            from src.helper.Secrets import get_secret
            self.db.initialize(MySQLDatabase(
                get_secret('mysql_database_name'),
                user=get_secret('mysql_user'),
                password=get_secret('mysql_password'),
                host=get_secret('mysql_host'),
                port=3306,
                ssl=True
            ))
        else:
            print("Running with Sqlite Backend")
            self.db.initialize(SqliteExtDatabase(
                os.getenv('DATABASE_PATH', 'cloud-billing.db'),
                regexp_function=True
            ))

    def disable_resource_index(self):
        if os.getenv('USE_MYSQL') == 'True':
            Settings().db.execute_sql('ALTER TABLE `resource` DISABLE KEYS;')

    def enable_resource_index(self):
        if os.getenv('USE_MYSQL') == 'True':
            Settings().db.execute_sql('ALTER TABLE `resource` ENABLE KEYS;')

    def get_default_sap_service_product_nr(self, provider):
        default_service_product_nrs = {
            Constants.AzureProvider: os.environ['Default_Constants_AzureProvider'],
            Constants.AwsProvider: os.environ['Default_Constants_AWSProvider'],
            Constants.ManagedCloudServices: os.environ['Default_Constants_ManagedCloudServices'],
            Constants.GCPProvider: os.environ['Default_Constants_GCPProvider']
        }

        return default_service_product_nrs.get(provider)

    def get_provider_from_sap_service_product_nr(self, default_sap_service_product_nr):
        default_service_product_nrs = {
            os.environ['Default_Constants_AzureProvider'] : Constants.AzureProvider,
            os.environ['Default_Constants_AWSProvider'] : Constants.AwsProvider,
            os.environ['Default_Constants_ManagedCloudServices'] : Constants.ManagedCloudServices,
            os.environ['Default_Constants_GCPProvider'] : Constants.GCPProvider
        }

        return default_service_product_nrs.get(default_sap_service_product_nr)
