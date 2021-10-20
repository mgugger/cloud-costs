from flask_admin.contrib.peewee import ModelView
from src.helper.User import current_user_roles

class AdditionalInvoicePositionView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()