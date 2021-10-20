import abc
import datetime
import os
import hvac
from src.model.DataImport import DataImport
from src.model.Resource import Resource
from src.helper.AccountHelper import AccountHelper
from src.helper.TagHelper import TagHelper
from src.settings import Settings
from src.helper.Secrets import get_secret, get_secret_path, get_param
from peewee import IntegrityError

class ImportBase():
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_files(self):
        """Retrieve files or urls to import"""
        return

    def __init__(self):
        self.PARAMETER = []
        self.SECRETS = []
        self.import_data=None
        self.imported_resources=[]
        self.accountHelper = AccountHelper()
        self.tagHelper = TagHelper()
        self.data_import = None
        self.job_name = None

    def get_secret(self, secret):
        return get_secret(secret)

    def get_param(self, param):
        return get_param(param)

    def get_secret_path(self, secret_path):
        return get_secret_path(secret_path)

    def create_data_import(self, file):
        data_import = DataImport.create(
            provider=type(self).__name__,
            start_time=datetime.datetime.now(),
            data_import_key=f"{self.job_name}/{file}")
        return data_import

    @abc.abstractmethod
    def run_import(self):
        """Retrieve data from the input source and return an object."""
        return

    @abc.abstractmethod
    def get_data_import_key(self):
        """Get the unique key for the data import."""
        return

    @abc.abstractmethod
    def get_resources(self, import_data):
        """Retrieve resources"""
        return

    def run(self, *sample_import_files):
        for param in self.PARAMETER:
            if not self.get_param(param):
                raise Exception(f"param {param} not set")

        for secret in self.SECRETS:
            secret_value = None
            # Do not fail if one of these secrets is set
            try:
                secret_value = self.get_secret(secret)
            except KeyError:
                pass
            except hvac.exceptions.Forbidden:
                pass

            # for secrets such as json mounted in their own path
            if not secret_value:
                try:
                    secret_value = self.get_secret_path(secret)
                except KeyError:
                    pass
                except hvac.exceptions.Forbidden:
                    pass

            if not secret_value:
                raise Exception(f"secret {secret} not set")

        if not sample_import_files:
            files=self.get_files()
        else:
            files = sample_import_files

        for file_to_import in files:
            print(f"Importing file {file_to_import}")
            try:
                self.data_import=self.create_data_import(file_to_import)

                import_data = self.run_import(file_to_import)

                if os.getenv('WRITE_IMPORTED_DATA_TO_FILE') == 'True':
                    f = open("out.txt", "w")
                    f.write(import_data)
                    f.close()

                if import_data:
                    resources = self.get_resources(import_data)
                    self.save(resources)

                self.data_import.end_time=datetime.datetime.now()
                self.data_import.save(only=[DataImport.end_time])
            except IntegrityError as e:
                raise Exception(e)
            except Exception as e:
                self.data_import.delete_instance()
                raise Exception(e)

    def chunks(self, l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def save(self, resources):
        with Settings().db.atomic() as transaction:
            try:
                Settings().disable_resource_index()

                for chunk in self.chunks(resources, 10000):
                    Resource.insert_many(chunk).execute()

                Settings().enable_resource_index()
            except ErrorSavingData as e:
                transaction.rollback()
                raise Exception(e)
