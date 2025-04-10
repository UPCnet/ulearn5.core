import json
from functools import wraps
from AccessControl.SecurityManagement import newSecurityManager
import urllib.parse
# We name it ploneapi to avoid conflicts with api.py file
from plone import api as ploneapi

""" Checker decorators for the API """


def check_methods(methods=[]):
    """
    Decorator that checks if the method used to call the endpoint is valid.
    """
    def wrapper(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            if self.request.method not in methods:
                raise MethodNotAllowed(f"Method not allowed: {self.request.method}")

            return func(self, *args, **kwargs)
        return wrapped_function
    return wrapper


def check_required_params(params=[]):
    """
    Decorator that checks the needed params are passed.
    """
    def wrapper(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            try:
                # Intenta cargar parámetros del cuerpo de la solicitud
                body_params = json.loads(self.request['BODY'])
            except:
                body_params = self.request.form

            # Procesa los parámetros de la query string
            query_string = self.request.get('QUERY_STRING', '')
            query_params = {key: value[0] for key, value in urllib.parse.parse_qs(query_string).items()}

            # Combina parámetros del cuerpo y de la query string
            all_params = {**body_params, **query_params}

            self.params = all_params  # Guarda todos los parámetros en self.params

            # Verifica que los parámetros requeridos estén presentes
            for param in params:
                if param not in all_params or not all_params[param]:
                    raise MissingParameters(f'Missing required parameter: {param}')

            # TODO: Comentado, no hace falta porque por ejemplo para la creación de usuarios pueden
            #       pasarnos más parametros de los requeridos
            # # Check for unexpected parameters
            # unexpected_params = set(body_params.keys()) - set(params)
            # if unexpected_params:
            #     raise BadParameters(
            #         f'Unexpected parameters: {", ".join(unexpected_params)}')

            return func(self, *args, **kwargs)
        return wrapped_function
    return wrapper


def check_roles(roles=[]):
    """
    Decorator that checks if the user has any of the roles passed as argument.
    """
    def wrapper(func):
        @wraps(func)
        def wrapped_function(self, *args, **kwargs):
            request = self.request
            oauth_user = request.get('HTTP_X_OAUTH_USERNAME', None)
            user = None
            if oauth_user:
                acl_users = self.context.acl_users
                user = acl_users.getUserById(oauth_user)
                if user:
                    # Autentica al usuario manualmente
                    newSecurityManager(request, user)
            else:
                user = ploneapi.user.get_current()

            if not user:
                raise Forbidden("User not found")

            user_roles = ploneapi.user.get_roles(user=user)

            if not user.has_role(roles):
                raise Forbidden('You are not allowed to access this resource')
            return func(self, *args, **kwargs)
        return wrapped_function
    return wrapper


""" Custom exceptions for the API """


class BadParameters(Exception):
    pass


class MissingParameters(Exception):
    pass


class ObjectNotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class MethodNotAllowed(Exception):
    pass


class UnknownEndpoint(Exception):
    pass
