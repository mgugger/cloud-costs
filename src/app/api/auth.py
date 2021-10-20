import os
from flask import session,redirect
from authlib.integrations.flask_client import OAuth

def create_flask_blueprint(backends, oauth, handle_authorize):
    """Create a Flask blueprint that you can register it directly to Flask
    app. The blueprint contains two route: ``/auth/<name>`` and
    ``/login/<name>``::

        from flask import Flask
        from authlib.integrations.flask_client import OAuth
        from loginpass import create_flask_blueprint, GitHub

        app = Flask(__name__)
        oauth = OAuth(app)


        def handle_authorize(remote, token, user_info):
            if token:
                save_token(remote.name, token)
            if user_info:
                save_user(user_info)
                return user_page
            raise some_error

        account_bp = create_flask_blueprint(
            oauth, [GitHub, Google], handle_authorize)
        app.register_blueprint(account_bp, url_prefix='/account')

        # visit /account/login/github
        # callback /account/auth/github

    :param oauth: Authlib Flask OAuth instance
    :param backends: A list of configured backends
    :param handle_authorize: A function to handle authorized response
    :return: Flask Blueprint instance
    """
    from flask import Blueprint, request, url_for, current_app, abort

    for b in backends:
        register_to(oauth, b)

    bp = Blueprint('loginpass', __name__)

    @bp.route('/auth/<name>', methods=('GET', 'POST'))
    def auth(name):
        remote = oauth.create_client(name)
        if remote is None:
            abort(404)

        id_token = request.values.get('id_token')
        if request.values.get('code'):
            token = remote.authorize_access_token()
            if id_token:
                token['id_token'] = id_token
        elif id_token:
            token = {'id_token': id_token}
        elif request.values.get('oauth_verifier'):
            # OAuth 1
            token = remote.authorize_access_token()
        else:
            # handle failed
            return handle_authorize(remote, None, None)
        if 'id_token' in token:
            user_info = remote.parse_id_token(token)
        else:
            remote.token = token
            user_info = remote.userinfo(token=token)
        return handle_authorize(remote, token, user_info)

    @bp.route('/login/<name>')
    def login(name):
        remote = oauth.create_client(name)
        if remote is None:
            abort(404)

        if os.getenv('DEBUG') == 'True':
            scheme = "http"
        else:
            scheme = "https"

        redirect_uri = url_for('.auth', name=name, _external=True, _scheme=scheme)
        conf_key = '{}_AUTHORIZE_PARAMS'.format(name.upper())
        params = current_app.config.get(conf_key, {})
        return remote.authorize_redirect(redirect_uri, **params)

    return bp

def register_to(oauth, backend_cls):
    from authlib.integrations.flask_client import FlaskRemoteApp

    class RemoteApp(backend_cls, FlaskRemoteApp):
        OAUTH_APP_CONFIG = backend_cls.OAUTH_CONFIG

    oauth.register(RemoteApp.NAME, overwrite=True, client_cls=RemoteApp)


def handle_authorize(remote, token, user_info):
    session['user'] = user_info
    return redirect('/')

def create_azure_backend(name, tenant, version=2, compliance_fix=None):

    base_url = 'https://login.microsoftonline.com/' + tenant
    if version == 1:
        metadata_url = base_url + '/.well-known/openid-configuration'
    elif version == 2:
        metadata_url = base_url + '/v2.0/.well-known/openid-configuration'
    else:
        raise ValueError('Invalid version value')

    class AzureAD(object):
        NAME = name
        OAUTH_CONFIG = {
            'api_base_url': 'https://graph.microsoft.com/',
            'server_metadata_url': metadata_url,
            'client_kwargs': {'scope': 'openid email profile'},
            'client_id': os.getenv('AZURE_CLIENT_ID', 'not_set'),
            'client_secret': os.getenv('AZURE_CLIENT_SECRET', 'not_set')
        }

        def load_server_metadata(self):
            metadata = super(AzureAD, self).load_server_metadata()
            if compliance_fix:
                metadata = compliance_fix(metadata)
            return metadata

    return AzureAD

backends = [create_azure_backend('azure', os.getenv('AZURE_TENANT_ID', "xxxx"))]
oauth = OAuth()
auth_api = create_flask_blueprint(backends, oauth, handle_authorize)

@auth_api.route('/logout')
def logout():
    session['user'] = None
    return redirect('/')
