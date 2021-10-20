import os
import datetime
from calendar import monthrange
import requests

from src.importer.ImportBase import ImportBase
from src.mapper.CsvMapper import CsvMapper
from src.constants import Constants

TODAY = datetime.date.today()
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH = FIRSTDAY - datetime.timedelta(days=1)
MONTHRANGE = monthrange(LASTMONTH.year, LASTMONTH.month)

class AzureImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.PARAMETER = [
            f"{job_name}_azure_enrollment_number"
        ]
        self.SECRETS = [
            f"{job_name}_azure_api_key",
        ]

    def get_files(self):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            return ['sample_files/azure.csv', 'sample_files/hadoop.csv']

        return ['usagedetails/download?billingPeriod=' + str(LASTMONTH.year) + f"{LASTMONTH.month:02d}"]

    def run_import(self, file_to_import):
        return_value = None

        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            f = open(file_to_import, "r")
            import_data = f.read()
            f.close()
            return_value = import_data
        else:
            CSVURL = f'https://consumption.azure.com/v3/enrollments/{self.get_param(self.PARAMETER[0])}/{file_to_import}'
            HEADERS = {'Authorization': f'bearer {self.get_secret(self.SECRETS[0])}',
            'Accept': 'application/json', "Accept-Language": "en-US,en;q=0.5"}
            R = requests.get(CSVURL, headers=HEADERS, verify=False)
            if R.status_code != 200:
                raise Exception(R.text)
            else:
                return_value = R.text
                import_data = R.text

        return return_value

    def get_resources(self, import_data):
        mapper = CsvMapper()
        mapper.set_mappings({
            'account': lambda x: self.accountHelper.get_account(x['Nom de l\'abonnement (SubscriptionName)'], x['Guid d\'abonnement (SubscriptionGuid)'], 'Azure', x['Centre de coûts (CostCenter)']),
            'service': lambda x: x['Service consommé (ConsumedService)'],
            'category': lambda x: x['Catégorie du compteur (MeterCategory)'],
            'region': lambda x: x['Région du compteur (MeterRegion)'],
            'quantity': lambda x: x['Quantité consommée (ConsumedQuantity)'],
            'cost': lambda x: x['Coût (Cost)'],
            'tags': lambda x: x['Balises (Tags)'],
            'cost_center': lambda x: self.tagHelper.get_cost_center(x['Balises (Tags)'], x['Centre de coûts (CostCenter)']),
            'date': lambda x: x['Date (Date)'],
            'provider': lambda x: Constants.AzureProvider,
            'instance_id': lambda x: x['ID d\'instance (InstanceId)'].split('/')[-1],
            'service_component': lambda x: self.tagHelper.get_service_component(x['Balises (Tags)']),
            'term': lambda x: None
        })

        return mapper.get_resources_as_dicts(import_data, self.data_import, 2)
