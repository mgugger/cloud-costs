import os
import datetime
from calendar import monthrange
import requests

from src.importer.ImportBase import ImportBase
from src.mapper.JsonMapper import JsonMapper

TODAY = datetime.date.today()
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH_FIRSTDAY = (FIRSTDAY - datetime.timedelta(days=1)).replace(day=1)
LASTMONTH_LASTDAY = LASTMONTH_FIRSTDAY.replace(day=monthrange(LASTMONTH_FIRSTDAY.year, LASTMONTH_FIRSTDAY.month)[1])

class AzureMarketPlaceImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.PARAMETER = [
            f"{job_name}_azure_enrollment_number"
        ]
        self.SECRETS = [
            f"{job_name}_azure_api_key"
        ]

    def get_files(self):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            return ['sample_files/azureMarketplace.json']
        else:
            return ['marketplacechargesbycustomdate?startTime=' + LASTMONTH_FIRSTDAY.strftime("%Y-%m-%d") + "&endTime=" + LASTMONTH_LASTDAY.strftime("%Y-%m-%d")]

    def run_import(self, file_to_import):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            f = open(file_to_import, "r")
            import_data = f.read()
            f.close()
            return import_data
        else:
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
            'service': lambda x: x['offerName'],
            'category': lambda x: x.get('planName', None),
            'region': lambda x: None,
            'quantity': lambda x: x['consumedQuantity'],
            'cost': lambda x: x['extendedCost'],
            'tags': lambda x: x['tags'],
            'cost_center': lambda x: x['costCenter'],
            'account' : lambda x: self.accountHelper.get_account(x['subscriptionName'], x['subscriptionGuid'], 'Azure'),
            'date': lambda x: x['usageStartDate'],
            'instance_id': lambda x: x.get('instanceId', None),
            'term': lambda x: None,
            'service_component': lambda x: self.tagHelper.get_service_component(x['tags']),
        })

        return mapper.get_resources_as_dicts(import_data, self.data_import)
