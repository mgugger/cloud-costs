import time
import yaml
from kubernetes import client, config
from flask_admin.contrib.peewee import ModelView
from wtforms.fields import SelectField
from src.importer.ImportBase import ImportBase
from src.constants import Constants
from src.model import Config
from flask import flash
from src.helper.User import current_user_roles

class JobView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    column_searchable_list = ['name']
    column_list = ('name', 'application_settings', 
        'cronjob_schedule', 'command', 'secrets', 'parameter', 'rerun_cmd')

    edit_modal = True
    create_modal = True
    can_edit = True

    form_overrides = dict(
        command=SelectField,
        application_settings=SelectField
    )

    commands = []
    available_importers = [cls.__name__ for cls in ImportBase.__subclasses__()]
    for importer in available_importers:
        commands.append((f"import {importer}", f"import {importer}"))
    for provider in Constants.Providers:
        commands.append((f"bill {provider}", f"bill {provider}"))

    commands.append(("mailer", "mailer"))
    commands.append(("mgmt_mailer", "mgmt_mailer"))

    form_args = dict(
        command = dict(choices=commands),
        application_settings = dict(choices=[
            ("/env/prod.env", "/env/prod.env"),
            ("/env/qa.env", "/env/qa.env"),
            ("/env/dev.env", "/env/dev.env")
        ])
    )

    def on_model_change(self, form, model, is_created):
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()

        result = model.get_job_yaml()
        file = open('cronjob.yaml', 'w')
        file.write(result)
        file.close()

        flash(f"The following config parameters must be defined: {', '.join(model.parameter)}")
        flash(f"The following secrets must be defined: {', '.join(model.secrets)}")

        with open("cronjob.yaml") as file:
            dep = yaml.load(file)
            k8s_beta = client.BatchV1beta1Api()
            try:
                k8s_beta.delete_namespaced_cron_job(
                    name=model.name,
                    namespace="company2-cloudbilling-prod"
                )
                time.sleep(5)
            except:
                pass
            k8s_beta.create_namespaced_cron_job(
                body=dep,
                namespace="company2-cloudbilling-prod"
            )

    def on_model_delete(self, model):
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()

        k8s_beta = client.BatchV1beta1Api()
        k8s_beta.delete_namespaced_cron_job(
            name=model.name,
            namespace="company2-cloudbilling-prod"
        )

        Config.delete() \
            .where(Config.key.in_(model.parameter)) \
            .execute()
