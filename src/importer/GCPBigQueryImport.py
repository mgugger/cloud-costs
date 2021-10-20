import os
import json
import datetime
from calendar import monthrange
from decimal import Decimal
from functools import lru_cache
from forex_python.converter import CurrencyRates
from google.cloud import bigquery
from src.mapper.IteratorMapper import IteratorMapper
from src.constants import Constants
from src.importer.ImportBase import ImportBase

TODAY = datetime.date.today()
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH = FIRSTDAY - datetime.timedelta(days=1)
MONTHRANGE = monthrange(LASTMONTH.year, LASTMONTH.month)

class GCPBigQueryImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.PARAMETER = [
            f"{self.job_name}_bigquery_tablename"
        ]
        self.SECRETS = [
            "cloud-billing-gcp-serviceaccount"
        ]

    def get_files(self):
        return ['invoice.month=' + str(LASTMONTH.year) + f"{LASTMONTH.month:02d}"]

    def run_import(self, file_to_import):
        return_value = None

        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            raise Exception("Not Implemented")

        gcp_credentials = self.get_secret_path(self.SECRETS[0])
        service_account_info = json.dumps(gcp_credentials)
        text_file = open("gcp_credentials.json", "w")
        text_file.write(service_account_info)
        text_file.close()
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'gcp_credentials.json'
        client = bigquery.Client()
        os.remove(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])

        QUERY = (f"""
            Select billing_account_id, service.description, sum(cost) as cost, sum(usage.amount) as usage_amount, currency, IFNULL(project.id, service.description) as project_id, IFNULL(project.name, service.description) as project_name, location.region, TO_JSON_STRING(labels) as labels, min(usage_start_time) as usage_start_time
            FROM `{self.get_param(self.PARAMETER[0])}`
            where invoice.month = "{str(LASTMONTH.year) + f'{LASTMONTH.month:02d}'}"
            group by billing_account_id, currency, project.id , project.name, service.description, labels, location.region
            """
        )
        query_job = client.query(QUERY)  # API request
        return_value = query_job.result()

        return return_value

    def get_decimal(self, float_str):
        return Decimal(float_str)

    @lru_cache(maxsize=2048)
    def get_exchange_rate(self, currency):
        currency_rates = CurrencyRates()
        return Decimal(currency_rates.get_rate(currency, 'CHF'))

    def get_resources(self, import_data):
        mapper = IteratorMapper()
        mapper.set_mappings({
            'account': lambda x: self.accountHelper.get_account(x['project_name'], x['project_id'], 'GCP'),
            'service': lambda x: x['description'],
            'category': lambda x: None,
            'region': lambda x: x['region'],
            'quantity': lambda x: x['usage_amount'],
            'cost': lambda x: self.get_exchange_rate(x['currency']) * self.get_decimal(x['cost']),
            'tags': lambda x: x['labels'],
            'cost_center': lambda x: self.tagHelper.get_cost_center(x['labels'], None),
            'date': lambda x: x['usage_start_time'],
            'provider': lambda x: Constants.GCPProvider,
            'instance_id': lambda x: None,
            'service_component': lambda x: self.tagHelper.get_service_component(x['labels']),
            'term': lambda x: None
        })

        return mapper.get_resources_as_dicts(import_data, self.data_import)
