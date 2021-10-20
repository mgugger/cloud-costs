from argparse import ArgumentParser
from dotenv import load_dotenv
import os
import pkgutil
import logging

import sys, inspect

from src.importer import all_importer
from src.model import *

from src.settings import Settings

from src.constants import Constants
from src.invoicing.Invoicer import Invoicer
from src.invoicing.Mailer import Mailer
from src.helper.DatabaseCompressor import DatabaseCompressor
from src.app import app

def create_app():
    Settings().logger = logging.getLogger("gunicorn.error")
    print("create app")
    try:        
        init_db()
        flask_app = app.create_app()
        gunicorn_logger = logging.getLogger("gunicorn.error")
        flask_app.logger.handlers = gunicorn_logger.handlers
        flask_app.logger.setLevel(gunicorn_logger.level)

        return flask_app
    except Exception as e:
        print("exception {0}".format(repr(e)))
        Settings().logger.error(e)

def init_db():
    Settings().init_db()
    Settings().db.create_tables([Resource, ServiceType, Config, Account, Invoice, Service, ServiceComponent, ServiceCustomer, DataImport, ServiceComponent2Service, Job, AdditionalInvoicePosition, ServiceComponentPart])
    Settings().db.close()

def load_env(args):
    if args and args.env:
        from pathlib import Path  # python3 only
        env_path = Path(args.env)
        load_dotenv(dotenv_path=env_path)
        print('loaded env from argument')
    elif os.environ.get('APPLICATION_SETTINGS'):
        load_dotenv(dotenv_path=os.environ['APPLICATION_SETTINGS'])
        print('loaded env from APPLICATION_SETTINGS environment file')
    else:
        print("No application environments provided")

if __name__ == "__main__":
    # Arg Parse   
    parser = ArgumentParser(add_help = False)
    parser.add_argument("-e", "--env", required=False)

    subparsers = parser.add_subparsers(title="cmd", dest="cmd")
    
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("importer", choices=all_importer, help="the importer to run")
    import_parser.add_argument("-n", "--name", action="store", required=True, help="the job name")
    import_parser.add_argument("-f", "--import-file", action="store", help="optional import file")

    bill_parser = subparsers.add_parser("bill")
    bill_parser.add_argument("provider", action="store", choices=Constants.Providers, help="The invoices to send")
    bill_parser.add_argument("-n", "--name", action="store", required=True, help="the job name")
    
    run_parser = subparsers.add_parser("run", help="Run the admin app")
    
    compress_parser = subparsers.add_parser("compress", help="Compresses the db by joining resource rows with same content and summing the cost")
    compress_parser.add_argument("-n", "--name", action="store", required=True, help="the job name")

    mail_parser = subparsers.add_parser("mailer", help="Send mails with last billing info to all customers")
    mail_parser.add_argument("-n", "--name", action="store", required=True, help="the job name")

    migrate_parser = subparsers.add_parser("migrate", help="Run the admin app")
    migrate_parser.add_argument("migrate_module", action="store", help="Run a mysql migrate script from src/migrations")

    upload_parser =subparsers.add_parser("upload", help="Uploads the file through the comadapter")
    upload_parser.add_argument("--file", action="store", required=True, help="path to the csv file")
    upload_parser.add_argument("--provider", action="store", required=True, choices=Constants.Providers)
    
    args = parser.parse_args()

    load_env(args)

    if args.cmd == "run":
        # init app & db
        flask_app = create_app()
        flask_app.run(debug=os.getenv('DEBUG') == 'True')
    else:
        # only init db
        init_db()

    if args.cmd == "import":
        import importlib
        klazz = getattr(importlib.import_module("src.importer.{importer}".format(importer=args.importer)), args.importer)
        instance = klazz(args.name)
        print("Running import with {importer}".format(importer=args.importer))
        if args.import_file:
            instance.run(args.import_file)
        else:
            instance.run()

    elif args.cmd == "bill":
        print("Running invoicer with {importer}".format(importer=args.provider))
        csv = Invoicer.invoice_resources(args.provider)

    elif args.cmd == "upload":
        print("Upload file with {provider}".format(provider=args.provider))
        with open(args.file, 'r') as file:
            csv_string = file.read()
            Invoicer.upload_file(csv_string, args.provider)
            print("file has been uploaded")

    elif args.cmd == "compress":
        print("Compressing database")
        DatabaseCompressor.compress()

    elif args.cmd == "mailer":
        print("Sending mail info to all service customers about last billing cycle")
        Mailer.send_mails_with_last_billing_info()

    elif args.cmd == "migrate":
        import importlib
        print("Migrating schema")
        klazz = getattr(importlib.import_module("src.migrations.{migrate}".format(migrate=args.migrate_module)), "MigrateDb")
        instance = klazz()
        instance.run()