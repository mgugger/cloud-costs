import datetime
from dateutil.relativedelta import relativedelta
import boto3
from src.importer.ImportBase import ImportBase

TODAY = datetime.date.today() + relativedelta(months=+1)
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH = (FIRSTDAY - datetime.timedelta(days=1)).replace(day=1)

class AwsAccountImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.SECRETS = [
            "aws_access_key_id",
            "aws_secret_access_key_id"
        ]

    def get_files(self):
        return ["AwsAccountImport{}".format(TODAY.strftime("%Y%m%d"))]

    def run_import(self, file_to_import):
        client = boto3.client('organizations',
             aws_access_key_id=self.get_secret(self.SECRETS[0]),
            aws_secret_access_key=self.get_secret(self.SECRETS[1])
        )
        accounts = []
        next_token = ''

        # list_accounts() returns a NextToken if results are paginated
        # list accounts while a next_token is returned
        while next_token is not None:
            if next_token == '':
                response = client.list_accounts()
            else:
                response = client.list_accounts(NextToken=next_token)

            next_token = response.get('NextToken', None)
            accounts.extend(response['Accounts'])

        return accounts

    def get_resources(self, import_data):
        for org_account in import_data:
            account = self.accountHelper.get_aws_account(org_account['Id'], 'AWS')
            account.account_name = org_account['Name']
            account.save()

        return []
