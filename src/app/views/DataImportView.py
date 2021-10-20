from flask_admin.contrib.peewee import ModelView
from src.helper.User import current_user_roles

class DataImportView(ModelView):
    column_default_sort = ('start_time', True)

    def is_accessible(self):
        return "admin" in current_user_roles()
