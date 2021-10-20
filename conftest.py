from pathlib import Path
import pytest
from dotenv import load_dotenv
from src.settings import Settings
import logging

env_path = Path('./env') / 'test.env'

def init_db():
    from src.model import Account, ServiceType, Invoice, Resource, DataImport, \
        ServiceComponentPart, ServiceComponent, ServiceCustomer, Service, \
        ServiceComponent2Service, AdditionalInvoicePosition, Config, Job
    Settings().init_db()
    Settings().db.connect()
    Settings().logger = logging.getLogger("flask")
    Settings().db.execute_sql('PRAGMA foreign_keys = ON')
    Settings().db.create_tables([
        Config,
        Account,
        ServiceComponentPart,
        ServiceType,
        Invoice,
        Resource,
        Job,
        DataImport,
        ServiceComponent,
        ServiceCustomer,
        Service,
        ServiceComponent2Service,
        AdditionalInvoicePosition
    ])

@pytest.fixture(scope="module")
def db():
    load_dotenv(dotenv_path=env_path)

    init_db()
    yield Settings().db

    Settings().db.close()

@pytest.fixture()
def test_client():
    load_dotenv(dotenv_path=env_path)

    init_db()
    from src.app import app
    flask_app = app.create_app()

    with flask_app.test_client() as client:
        yield client
