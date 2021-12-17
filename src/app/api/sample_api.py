from flask import Blueprint
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from src.helper.Secrets import get_secret

sample_api = Blueprint('sample_api', __name__, template_folder='templates')
auth = HTTPBasicAuth()

users = None

@auth.verify_password
def verify_password(username, password):
    global users 
    if not users:
        users = {
            "automation_user": generate_password_hash(get_secret("automationuser_httpauth_pw")),
        }

    if username in users and \
            check_password_hash(users.get(username), password):
        return username

@sample_api.route('/sample_api/do_something')
@auth.login_required
def do_something():
    # some logic here
    return "Hello, %s!" % auth.current_user()