import os
from flask import session

def current_user():
    if os.getenv('DEBUG') == 'True':
        return "test@test.com"

    if 'user' in session and session['user']:
        jwt = session['user'].get('email', None)
        return jwt
    return None

def current_user_roles():
    if os.getenv('DEBUG') == 'True':
        return "admin"

    if 'user' in session and session['user']:
        return session['user'].get('roles', [])
    return []
