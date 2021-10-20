from src.model.Account import Account
from src.model.ServiceCustomer import ServiceCustomer
from src.settings import Settings

class AccountHelper():
    def __init__(self):
        self.account_dictionary = {}

    def get_account(self, account_name, account_id, provider, cost_center=None):
        dict_key = f'{account_name}{account_id}{provider}'
        account = self.account_dictionary.get(
            dict_key,
            Account.get_or_none(
                account_name = account_name,
                account_id = account_id,
                provider = provider
            )
        )
        if not account:
            service_customer = None
            if cost_center:
                service_customer = ServiceCustomer.get_or_none(cost_center=cost_center)
                if not service_customer:
                    service_customer = ServiceCustomer.create(cost_center=cost_center, name="TODO")
            account = Account.create(
                account_name = account_name,
                service_customer=service_customer,
                account_id = account_id,
                cost_center = cost_center,
                provider = provider,
                sap_service_product_nr = Settings().get_default_sap_service_product_nr(provider)
            )
            account.save()
            self.account_dictionary[dict_key] = account
        return account

    def get_aws_account(self, account_id, provider):
        dict_key = f'{account_id}{provider}'
        account = self.account_dictionary.get(
            dict_key,
            Account.get_or_none(account_id = account_id, provider = provider)
        )
        if not account:
            account = Account.create(
                account_id = account_id,
                account_name = "AWS",
                provider = provider,
                sap_service_product_nr = Settings().get_default_sap_service_product_nr(provider)
            )
            account.save()
            self.account_dictionary[dict_key] = account
        return account
