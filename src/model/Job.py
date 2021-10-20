import importlib
from string import Template
from peewee import Model, CharField
from src.settings import Settings

class Job(Model):
    name = CharField(index=True)
    application_settings = CharField(index=False)
    cronjob_schedule = CharField(index=False)
    command = CharField(index=False)

    @property
    def secrets(self):
        try: # this does not work for billing
            commands = str(self.command).split(" ")
            klazz = getattr(importlib.import_module(f"src.importer.{commands[1]}"), commands[1])
            instance = klazz(job_name = self.name)
            return instance.SECRETS
        except Exception as e:
            print(e)
            return []

    @property
    def parameter(self):
        try: # this does not work for billing
            commands = str(self.command).split(" ")
            klazz = getattr(importlib.import_module(f"src.importer.{commands[1]}"), commands[1])
            instance = klazz(job_name = self.name)
            return instance.PARAMETER
        except Exception as e:
            print(e)
            return []

    @property
    def rerun_cmd(self):
        cmd = f"kubectl create job --from=cronjob/{self.name} {self.name}-manual -n $NAMESPACE"
        return cmd

    def get_job_yaml(self):
        filein = open( 'src/resources/k8s_cronjob.yaml' )
        src = Template( filein.read() )
        commands = str(self.command).split(" ")
        if len(commands) > 1:
            command = f'["python", "run.py", "{commands[0]}", "{commands[1]}", "-n", "{self.name}"]'
        else:
            command = f'["python", "run.py", "{commands[0]}", "-n", "{self.name}"]'

        d={
            'name':self.name,
            'command':command,
            'cronjob_schedule': self.cronjob_schedule,
            'application_settings': self.application_settings
        }
        result = src.substitute(d)
        return result

    class Meta:
        database = Settings().db
