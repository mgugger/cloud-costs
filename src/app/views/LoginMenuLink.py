from flask_admin.menu import MenuLink
from src.helper.User import current_user

class LoginMenuLink(MenuLink):

    def is_accessible(self):
        return not current_user()

class LogoutMenuLink(MenuLink):
    def is_accessible(self):
        return current_user()