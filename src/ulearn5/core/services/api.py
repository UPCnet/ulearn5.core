from minimal.core.services import UnknownEndpoint
from minimal.core.services.appconfig import AppConfig
from minimal.core.services.banners import Banners
from minimal.core.services.communities import Communities
from minimal.core.services.events import Events
from minimal.core.services.folders import Folders
from minimal.core.services.groups import Groups
from minimal.core.services.item import Item
from minimal.core.services.links import Links
from minimal.core.services.news import News
from minimal.core.services.notifications import Notifications
from minimal.core.services.notifymail import Notifymail
from minimal.core.services.notnotifymail import Notnotifymail
from minimal.core.services.notnotifypush import Notnotifypush
from minimal.core.services.people import People
from minimal.core.services.profile import Profile
from minimal.core.services.profilesettings import ProfileSettings
from minimal.core.services.saveeditacl import SaveEditACL
from plone.restapi.services import Service
from zope.interface import implementer
from zope.publisher.interfaces.browser import IBrowserPublisher


@implementer(IBrowserPublisher)
class APIBase(Service):
    """
    Base service, used to manage subpaths of @api
    """

    PATH_DICT = {
        "appconfig": AppConfig,
        "banners": Banners,
        "communities": Communities,
        "saveeditacl": SaveEditACL,
        "notnotifymail": Notnotifymail,
        "notnotifypush": Notnotifypush,
        "notifymail": Notifymail,
        "events": Events,
        "folders": Folders,
        "groups": Groups,
        "item": Item,
        "links": Links,
        "news": News,
        "notifications": Notifications,
        "people": People,
        "profilesettings": ProfileSettings,
        "profile": Profile,
    }

    def __init__(self, context, request):
        super().__init__(context, request)
        self.subpath = []

    def publishTraverse(self, request, name):
        """
        Store dynamic path parts (after @api) in self.subpath
        """
        self.subpath.append(name)
        return self

    def browserDefault(self, request):
        """
        Error handling. Must be here to avoid errors
        """
        return self, ()

    def reply(self):
        """
        Main method. Calls the corresponding handler for the subpath
        """
        if not self.subpath:
            # Plain petition to @api (no subpath)
            return {"message": "Welcome to the API base", "code": 200}

        # Identifying the subpath (first segment after @api)
        route = self.subpath[0]
        handler_class = self.PATH_DICT.get(route)

        if handler_class:
            # Send parameters (query or body) to the handler
            kwargs = {key: value for key, value in self.request.form.items()}

            # Call the corresponding handler
            handler = handler_class(self.context, self.request, **kwargs)
            return handler.handle_subpath(self.subpath[1:])

        # Path not found in PATH_DICT
        raise UnknownEndpoint(f"Unknown endpoint: {route}")
