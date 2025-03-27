import json
from functools import wraps

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
                body_params = json.loads(self.request['BODY'])
            except:
                body_params = self.request.form

            self.params = body_params
            for param in params:
                if param not in body_params:
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
            user = ploneapi.user.get_current()
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
