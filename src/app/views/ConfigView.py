from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterLike
from src.helper.User import current_user_roles
from src.model import Config, Job

class ConfigView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    def get_jobs():
        return [(x.name, x.name) for x in Job.select().execute()]

    column_filters = [
        FilterLike(Config.key, 'Job', options=get_jobs)
    ]

    column_searchable_list = ['key', 'value']
    column_editable_list = ('value')
