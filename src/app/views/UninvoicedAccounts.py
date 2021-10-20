import math
from flask_admin import BaseView, expose
from flask import request
from peewee import fn
from src.model import Account, Resource
from src.helper.User import current_user

class UninvoicedAccounts(BaseView):
    def is_accessible(self):
        return current_user() is not None

    @expose('/')
    def index(self):
        provider = request.args.get('provider', None)
        accounts = Account.select(
                Account.account_name,
                Account.provider,
                fn.SUM(Resource.cost).alias('cost')
            ) \
            .join(Resource) \
            .where(Resource.invoice.is_null()) \
            .group_by(Account.account_name) \
            .order_by(Account.provider, fn.SUM(Resource.cost).desc())

        if provider:
            accounts = accounts.where(Account.provider == provider)

        return self.render(
            'uninvoiced_accounts.html',
            uninvoiced_accounts=accounts.dicts(),
            math=math
        )
