from flask_admin.contrib.peewee import ModelView
from src.helper.User import current_user_roles
from flask import flash
from src.helper.QueryHelper import delete_invoice_helper
import threading

class InvoiceView(ModelView):
    column_searchable_list = ['provider', 'output']
    can_edit = False
    column_default_sort = ('date', True)
    can_export = True

    def is_accessible(self):
        return "admin" in current_user_roles()

    def delete_model(self, model):
        delete_thread = threading.Thread(target=delete_invoice_helper, args=(model,))
        delete_thread.start()
        flash("Delete scheduled in background", "info")
        return False
