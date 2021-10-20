from flask_admin.contrib.peewee import ModelView
from src.helper.User import current_user_roles

class ServiceCustomerReadOnly(ModelView):
    def is_accessible(self):
        return "admin" not in current_user_roles()

    column_searchable_list = ('cost_center', 'name', 'account_owner_email')
    column_exclude_list = ('account_owner_email')

    can_export = True
    can_create = False
    can_edit = False
    can_delete = False
