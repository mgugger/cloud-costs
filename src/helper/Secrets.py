import os
from functools import lru_cache
import hvac
from src.model import Config

@lru_cache(maxsize=128)
def get_param(param):
    config = Config.get_or_none(key=param)
    if not config:
        secret = "TODO"
        try:
            secret = get_secret(param)
        except KeyError:
            pass
        config = Config.create(key=param, value=secret)
    return config.value

def get_secret(secret):
    secret_client = None
    if os.environ.get('USE_VAULT', "True") == "False":
        return "dev"

    if not secret_client:
        secret_client = hvac.Client(url=os.environ['VAULT_URL'])
        if os.environ.get('VAULT_ROLE_ID', None) and os.environ.get('VAULT_ROLE_SECRET_ID', None):
            secret_client.auth_approle(
                os.environ['VAULT_ROLE_ID'],
                os.environ['VAULT_ROLE_SECRET_ID']
                )
        else:
            secret_client.token = os.environ['VAULT_TOKEN']

    secret_version_response = secret_client.secrets.kv.read_secret_version(
        mount_point=os.environ['VAULT_MOUNT_POINT'],
        path=os.environ['VAULT_SECRET_PATH']
    )
    return secret_version_response['data']['data'][secret]

@lru_cache(maxsize=128)
def get_secret_path(secret_path):
    secret_client = None
    if os.environ.get('USE_VAULT', "True") == "False":
        return "dev"

    if not secret_client:
        secret_client = hvac.Client(url=os.environ['VAULT_URL'])
        secret_client.auth_approle(
            os.environ['VAULT_ROLE_ID'], 
            os.environ['VAULT_ROLE_SECRET_ID']
            )

    secret_version_response = secret_client.secrets.kv.read_secret_version(
        mount_point=os.environ['VAULT_MOUNT_POINT'],
        path=secret_path
    )
    return secret_version_response['data']['data']
