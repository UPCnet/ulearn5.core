# -*- coding: utf-8 -*-
from Products.Five.browser import BrowserView
from zope.component.hooks import getSite

import inspect
import importlib


MODULES_TO_INSPECT = [
    "base5.core.setup",
    "ulearn5.core.browser.setup",
]


class clouseau(BrowserView):

    def get_helpers(self):
        absolute_url = getSite().absolute_url()

        result = {
            "plone_site": [],
            "elastic": [],
            "ldap": [],
        }

        for module in MODULES_TO_INSPECT:
            themodule = importlib.import_module(module)
            members = inspect.getmembers(themodule, inspect.isclass)

            for name, klass in members:
                if "ulearn5." in str(klass):
                    if "LDAP" in name or "ldap" in name:
                        result["ldap"].append(
                            dict(
                                url="{}/{}".format(absolute_url, name),
                                description=klass.__doc__,
                            )
                        )
                    elif "Elastic" in name or "elastic" in name:
                        result["elastic"].append(
                            dict(
                                url="{}/{}".format(absolute_url, name),
                                description=klass.__doc__,
                            )
                        )
                    else:
                        result["plone_site"].append(
                            dict(
                                url="{}/{}".format(absolute_url, name),
                                description=klass.__doc__,
                            )
                        )

        return result
