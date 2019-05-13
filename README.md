# ulearn5.core
Ulearn5 Core és el paquet base de comunitats

[![Build Status](https://travis-ci.org/UPCnet/ulearn5.core.svg?branch=master)](https://travis-ci.org/UPCnet/ulearn5.core)  [![Coverage Status](https://coveralls.io/repos/github/UPCnet/ulearn5.core/badge.svg)](https://coveralls.io/github/UPCnet/ulearn5.core)

Installation
============
Al instal·lar aquest paquet s'instal·len tots els paquets de la base de comunitats.


Information
===========



Testing
=======

Open console and execute:

    Execute all of tests:

        ./bin/test -s ulearn5.core

    Or, individually:

        ./bin/test -s ulearn5.core -t test_api
        ./bin/test -s ulearn5.core -t test_communities
        ./bin/test -s ulearn5.core -t test_gwuuid
        ./bin/test -s ulearn5.core -t test_ldap
        ./bin/test -s ulearn5.core -t test_portlet_calendar
        ./bin/test -s ulearn5.core -t test_search
        ./bin/test -s ulearn5.core -t test_sharing
