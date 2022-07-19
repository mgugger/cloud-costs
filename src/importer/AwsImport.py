import os
import tempfile
import datetime
from decimal import Decimal
import zipfile
import boto3
from forex_python.converter import CurrencyRates
from src.importer.ImportBase import ImportBase
from src.mapper.CsvMapper import CsvMapper
from src.constants import Constants

TODAY = datetime.date.today()
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH = (FIRSTDAY - datetime.timedelta(days=1)).replace(day=1)

class AwsImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.SECRETS = [
            "aws_access_key_id",
            "aws_secret_access_key_id"
        ]

    def get_files(self):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            return ['sample_files/AWSBilling/20190601-20190701/AWSBilling-00001.csv.zip']
        else:
            s3 = boto3.resource('s3',
                aws_access_key_id=self.get_secret(self.SECRETS[0]),
                aws_secret_access_key=self.get_secret(self.SECRETS[1])
            )
            my_bucket = s3.Bucket('billing-m')
            folder_prefix = f"DailyAWSBillingReport/AWSBilling/{LASTMONTH.strftime('%Y%m%d')}-{FIRSTDAY.strftime('%Y%m%d')}"
            print('Looking in folder {}'.format(folder_prefix))
            return [csv for csv in my_bucket.objects.filter(Prefix=folder_prefix) if csv.key.endswith('.csv.zip')]

    def extract_zip(self, input_zip):
        input_zip=zipfile.ZipFile(input_zip)
        return input_zip.read(input_zip.namelist()[0])

    def run_import(self, file_to_import):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            binary_data = self.extract_zip(file_to_import)
            return binary_data.decode()
        else:
            with tempfile.TemporaryFile() as f:
                s3 = boto3.resource('s3',
                    aws_access_key_id=self.get_secret('aws_access_key_id'),
                    aws_secret_access_key=self.get_secret('aws_secret_access_key_id')
                )
                obj = s3.Object(file_to_import.bucket_name, file_to_import.key)
                obj.download_fileobj(f)
                f.seek(0)
                binary_data = self.extract_zip(f)
                return binary_data.decode()

    def get_decimal(self, float_str, default_value):
        try:
            return Decimal(float_str)
        except ValueError:
            return Decimal(default_value)

    def get_exchange_rate(self):
        c = CurrencyRates()
        return c.get_rate('USD', 'CHF')

    def get_resources(self, import_data):
        exchange_rate = self.get_exchange_rate()

        mapper = CsvMapper()
        mapper.set_mappings({
            'account': lambda x: self.accountHelper.get_aws_account(x['lineItem/UsageAccountId'], 'AWS'),
            'service': lambda x: x['product/servicename'],
            'category': lambda x: x['product/ProductName'],
            'region': lambda x: x['product/region'],
            'quantity': lambda x: x['lineItem/NormalizedUsageAmount'],
            'cost': lambda x: Decimal(exchange_rate) * (self.get_decimal(x['lineItem/UnblendedCost'], 0)),
            'tags': lambda x: None,
            'cost_center': lambda x: None,
            'date': lambda x: None, # Error: "Incorrect datetime value: '2019-06-13T12:07:57Z' for column `cloud-billing-qa`.`resource`.`date` at row 1") x['lineItem/UsageStartDate'],
            'provider': lambda x: Constants.AwsProvider,
            'instance_id': lambda x: x['lineItem/ResourceId'],
            'service_component': lambda x: self.tagHelper.get_service_component_by_name(x.get('resourceTags/user:billing-service-component', None)),
            'term': lambda x: x['reservation/SubscriptionId'] if x['reservation/UnitsPerReservation'] else None
        })

        return mapper.get_resources_as_dicts(import_data, self.data_import)