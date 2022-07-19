import os
import datetime
from calendar import monthrange
import requests

from src.importer.ImportBase import ImportBase
from src.mapper.JsonMapper import JsonMapper

TODAY = datetime.date.today()
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH = FIRSTDAY - datetime.timedelta(days=1)
MONTHRANGE = monthrange(LASTMONTH.year, LASTMONTH.month)

class AzureReservedInstanceImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.PARAMETER = [
            "{job_name}_azure_enrollment_number"
        ]
        self.SECRETS = [
            f"{job_name}_azure_api_key"
        ]

    def get_files(self):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            return ['sample_files/azureReservedInstance.json']
        else:
            return [f'reservationcharges?startDate={str(LASTMONTH.year)}-{LASTMONTH.month:02d}-01T00:00:00Z&endDate={str(LASTMONTH.year)}-{LASTMONTH.month:02d}-{str(MONTHRANGE[1])}T23:59:59Z']

    def run_import(self, file_to_import):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            f = open(file_to_import, "r")
            import_data = f.read()
            f.close()
            return import_data

        CSVURL = f'https://consumption.azure.com/v3/enrollments/{self.get_param(self.PARAMETER[0])}/{file_to_import}'
        HEADERS = {'Authorization': f'bearer {self.get_secret(self.SECRETS[0])}',
        'Accept': 'application/json', "Accept-Language": "en-US,en;q=0.5"}
        R = requests.get(CSVURL, headers=HEADERS, verify=False)
        if R.status_code != 200:
            raise Exception(R.text)
        else:
            return R.text

    def get_resources(self, import_data):
        mapper = JsonMapper()
        mapper.set_mappings({
            'service': lambda x: x['armSkuName'],
            'category': lambda x: 'Reserved Instance',
            'region': lambda x: x['region'],
            'quantity': lambda x: x['quantity'],
            'cost': lambda x: x['amount'],
            'tags': lambda x: x['reservationOrderName'],
            'cost_center': lambda x: x['costCenter'],
            'account' : lambda x: self.accountHelper.get_account(x['purchasingSubscriptionName'], x['purchasingSubscriptionGuid'], 'Azure'),
            'date': lambda x: x['eventDate'],
            'instance_id': lambda x: x['description'],
            'term': lambda x: x['term'],
            'service_component': lambda x: None,
        })

        return mapper.get_resources_as_dicts(import_data, self.data_import)
