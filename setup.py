# -*- coding: utf-8 -*-
"""Installer for the ulearn5.core package."""

from setuptools import find_packages
from setuptools import setup


long_description = '\n\n'.join([
    open('README.rst').read(),
    open('CONTRIBUTORS.rst').read(),
    open('CHANGES.rst').read(),
])


setup(
    name='ulearn5.core',
    version='1.0a1',
    description="Core Comunitats Plone 5",
    long_description=long_description,
    # Get more from https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Plone",
        "Framework :: Plone :: 5.0",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords='Python Plone',
    author='Plone Team',
    author_email='plone.team@upcnet.es',
    url='https://pypi.python.org/pypi/ulearn5.core',
    license='GPL version 2',
    packages=find_packages('src', exclude=['ez_setup']),
    namespace_packages=['ulearn5'],
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'plone.api',
        'Products.GenericSetup>=1.8.2',
        'setuptools',
        'z3c.jbot',
        'five.grok',
        'pas.plugins.osiris',
        'plone.app.dexterity [grok]',
        'plone.app.contenttypes',
        'plone.app.event',
        'infrae.rest',
        'Products.PloneFormGen',
        'collective.z3cform.datagridfield',
        'souper',
        'collective.polls>=1.10b1',
        'zope.formlib',
        'base5.core',
        'base5.portlets',
        'ulearn5.theme',
        'mrs5.max',
        'unittest2'
    ],
    extras_require={
        'test': [
            'plone.app.testing',
            # Plone KGS does not use this version, because it would break
            # Remove if your package shall be part of coredev.
            # plone_coredev tests as of 2016-04-01.
            'plone.testing>=5.0.0',
            'plone.app.contenttypes',
            'plone.app.robotframework[debug]',
        ],
    },
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
