Changelog
=========


0.142 (unreleased)
------------------

- Nothing changed yet.


0.141 (2025-04-25)
------------------

* /api/userspropertiesmigration /api/migrationcommunities [pilar.marinas]
* [FIX] Traduccion [Iago López]

0.140 (2024-10-07)
------------------

* [UPD] Traducciones nuevo portlet [Iago López]

0.139 (2024-09-16)
------------------

* Merge remote-tracking branch 'origin/develop' [Iago López]
* [FIX] api/item [Iago López]
* [FIX] api/links - self.urlBelongsToCommunity(url, portal_url) -> urlBelongsToCommunity(url, portal_url) [Iago López]

0.138 (2024-08-06)
------------------

* [FIX] ulearn-stats-query [Iago López]

0.137 (2024-07-22)
------------------

* Update patches.py ADD administrador3 enginyersbcn [pmarinas]
* [FIX] Recovering old stats [Alberto Durán]
* [REMOVE] ipdb [Iago López]
* [ADD] urlBelongsToCommunity function to api/item [Alberto Durán]
* [FIX] html_parser evitar que pete si se limpia todo el html [Iago López]
* [FIX] Allow all contenttypes in menugestio links [Alberto Durán]
* [UPD] print stats with ga4 [Alberto Durán]
* [UPD] stats with ga4 [Alberto Durán]
* [FIX] timezone in api/events [Alberto Durán]
* [FIX] Returning if link belongs to community [Alberto Durán]
* [ADD] Recurrence to events endpoint [Alberto Durán]
* [UPD] api/links to get info when link is unaffordable [Alberto Durán]

0.136 (2024-01-09)
------------------

* Merge remote-tracking branch 'origin/develop' [Alberto Durán]
* [ADD] /api/folders?path=... used when items belong outside communities [Alberto Durán]
* [FIX] /api/links/{lang} is_community_belonged param [Alberto Durán]
* [UPD] /api/item to expand resolveuid urls [Alberto Durán]
* [FIX] Speed up /api/communities/{com}/documents without heavy unused properties [Alberto Durán]
* [FIX] HTML Parser for text in API and reorganize imports [Iago López]

0.135 (2023-12-18)
------------------

* Merge remote-tracking branch 'origin/develop' [Alberto Durán]
* [UPD] /api/links/{lang} added parameter is_community_belonged to each object [Alberto Durán]
* [FIX] api/people/x/ushare, no repetir campos fullname y email [Iago López]
* [UPD] /api/links/{lang} per a que retorni un objecte igual que la resta d'enllaços [Iago López]
* [UPD] /api/links/{lang} per a que retorni un objecte igual que la resta d'enllaços [Alberto Durán]
* [UPD] HTML Parser in different file [Alberto Durán]
* [FIX] api/banners orden [Iago López]
* [FIX] Api lower username [Iago López]
* [ADD] HTML Parser for text in API and reorganize imports [Alberto Durán]
* [FIX] util calculatePortalTypeOfInternalPath - Resolve UID [Iago López]

0.134 (2023-11-30)
------------------

* Merge remote-tracking branch 'origin/develop' [Alberto Durán]
* [FIX] /api/people/{user}/subscriptions - Que no pete si no esta suscrito a ninguna comunidad [Iago López]
* [FIX] /api/people/{user}/subscriptions - Que no pete si no esta suscrito a ninguna comunidad [Iago López]

0.133 (2023-11-30)
------------------

* Merge remote-tracking branch 'origin/develop' [Alberto Durán]
* [UPD] /api/item?url=... type_when_follow_url = item.portal_type for all content types [Alberto Durán]
* [UPD] /api/people/{username}/subscriptions to return only communities_subscribed_by_user [Alberto Durán]
* [ADD] can_write property to /api/communities/{community} [Alberto Durán]
* [UPD] Only show global banners in api calls [Alberto Durán]

0.132 (2023-11-15)
------------------

* [FIX] thumbnail-url imagenes png con transparencia [Iago López]
* [UPD] API /api/communities & /api/people/x/subscriptions para añadir url de la imagen por defecto de las comunidades [Iago López]
* [UPD] API /api/links/{lang} [Alberto Durán]
* API /api/profile [Iago López]
* [UPD] API api/banners [Iago López]
* API api/banners [Iago López]
* API /api/profilesettings [Iago López]
* [UPD] API /api/people/{username}/ushare [Iago López]
* API /api/people/{username}/ushare [Iago López]

0.131 (2023-09-20)
------------------

* Hook add, add Etherpad [Iago López]

0.130 (2023-05-30)
------------------

* Update external_url for Files and videos [Alberto Durán]

0.129 (2023-05-12)
------------------

* Push & AS with same message for all content types [Alberto Durán]
* [UPD] Add import [Iago López]
* [UPD] Añadir parametros de salida /api/people/{username}/subscriptions [Iago López]
* [UPD] Añadir parametros de salida /api/people/{username}/subscriptions [Iago López]
* [UPD] Arreglar indentacion /api/notifymail [Iago López]
* [UPD] Mantener transparencia en las imagenes del thumbnail-image [Iago López]

0.128 (2023-05-08)
------------------

* Add functionality to api/item to be able to manage push [Alberto Durán]
* [UPD] api/people/{username}/visualizations add import [Iago López]
* [UPD] api/people/{username}/subscriptions añadir nueva información de resultado, hash | image_url | pending + [ADD] api/people/{username}/visualizations [Iago López]

0.127 (2023-02-15)
------------------

* Can write in community [Pilar Marinas]

0.126 (2023-01-18)
------------------

* Modificado parche notificacion automatica por mail enginyers campo email y no email_ebcn [Pilar Marinas]
* Añadir vista estadisticas app solo para miranza [Pilar Marinas]

0.125 (2022-12-15)
------------------

* WS Notnotifypush para marcar y desmarcar la notificacion por mail de usuario - comunidad [Pilar Marinas]
* WS Notnotifypush para marcar y desmarcar la notificacion por mail de usuario - comunidad [Pilar Marinas]
* thumbnail-image fix error contenttype Image [Iago López]
* WS Notnotifymail para marcar y desmarcar la notificacion por mail de usuario - comunidad [Pilar Marinas]

0.124 (2022-10-17)
------------------

* Como no se utiliza y en el max 5.3.25 en las actividades esta bien escrito y en los comentarios no lo comento para que no de error [Pilar Marinas]

0.123 (2022-09-14)
------------------

* Fix bug when notifications are off [alberto.duran]
* Set correct url destination for internal links [alberto.duran]
* Give destination information for internal links [alberto.duran]
* Devolver un enlace descargable cuando se consulta un ExternalContent [alberto.duran]
* Change order of transformations in replaceImagePathByURL [alberto.duran]
* Testing agent 2 [alberto.duran]
* Remove whitespace, testing agent [alberto.duran]

0.122 (2022-07-27)
------------------

* Corregir errores al renderizar imagen [alberto.duran]

0.121 (2022-07-27)
------------------

* Reemplazar imágenes en notícias sólo si hay body [alberto.duran]
* Asegurar que el uid existe y reemplazar imágenes sólo si hay body [alberto.duran]
* Merge branch 'develop' of github.com:UPCnet/ulearn5.core into develop [alberto.duran]
* Replace resolve uids by external url to be able to load in app [alberto.duran]

0.120 (2022-07-20)
------------------

* Cambios nueva version elasticsearch 7.12.0 [root]
* Replace internal urls in events detail and add whole_day and open_end to events listing [alberto.duran]

0.119 (2022-07-14)
------------------

* Resolve bug when special items don't have state [alberto.duran]
* Corregir tabulación erronia [alberto.duran]
* Solucionar UnicodeEncodeError thumbnail-image [Pilar Marinas]
* Merge branch 'develop' of github.com:UPCnet/ulearn5.core into develop [alberto.duran]
* Add post for notifications [alberto.duran]

0.118 (2022-07-06)
------------------

* Buscar las imagenes internas y añadirles /thumbnail-image [alberto.duran]
* Get Notificaciones pop-up [alberto.duran]
* Endpoint to get an Event [alberto.duran]
* Endpoint that returns all events in community from start to end [alberto.duran]
* Canvi user test [Pilar Marinas]
* Solve some bugs [alberto.duran]
* Resolver bug al hacer la query al catalogo [alberto.duran]
* Vista del detalle de un objecto [alberto.duran]
* Search endpoint for documents folder inside communities [alberto.duran]

0.117 (2022-06-15)
------------------

* Endpoint that returns community structure [alberto.duran]
* Add hash to community and community detail endpoint [alberto.duran]
* Afegir a quina comunitat pertany la noticia (al detall de la noticia) [alberto.duran]
* Afegir a quina comunitat pertany la noticia [alberto.duran]
* Add image community to endpoint and if tabs must be showed or not [alberto.duran]
* Add booleans to be able to show customized community tabs in App [alberto.duran]
* More items a False [alberto.duran]
* API news: añadidos filtros por categoria y comunidad [alberto.duran]

0.116 (2022-03-28)
------------------

* Delete avatar user [Pilar Marinas]
* Parche para reordenar carpetas que no son ordenables (news, events, members) [Pilar Marinas]
* Solucionar error si ulearn_settings.url_site esta en blanco [Pilar Marinas]
* Add permission PloneFormGen [Pilar Marinas]

0.115 (2021-12-15)
------------------

* Utils user_id [ilopezsmx]

0.114 (2021-11-26)
------------------

* ULearn -> uShare [Iago López Fernández]

0.113 (2021-07-28)
------------------

* Notificaciones popup, cambiar annotation por soup [Iago López Fernández]
* Quitar annotation popup aniversario y hacer control con cookie [Iago López Fernández]
* Mejora para no llamar tanto al annotation de los popup [Iago López Fernández]

0.112 (2021-07-19)
------------------

* Traducciones [Iago López Fernández]

0.111 (2021-07-19)
------------------

* Quitar ScoresUtility generali no se utiliza [Pilar Marinas]
* blink -> blank [Iago López Fernández]
* Notificacions popup [Iago López Fernández]

0.110 (2021-07-15)
------------------

* controlpopup tinymce [Iago López Fernández]
* update_birthday_profile_by_mail [Iago López Fernández]
* Popups notificaciones [Iago López Fernández]

0.109 (2021-07-07)
------------------

* ScoresUtility migration generali [Pilar Marinas]
* Solucionar iframe si no hay texto [Pilar Marinas]
* Solucionar error migrationUsersProfilesSoup [Pilar Marinas]
* migrationUsersProfilesSoup [Pilar Marinas]

0.108 (2021-06-21)
------------------

* Notify by mail text and image in activity [Pilar Marinas]

0.107 (2021-06-14)
------------------

* Notify by mail activity and comment [Pilar Marinas]
* Quitar hook imagen [Iago López Fernández]
* PEP-8 [Iago López Fernández]

0.106 (2021-05-19)
------------------

* No notificar por mail si contenido esta dentro carpeta privada [Pilar Marinas]

0.105 (2021-05-18)
------------------

* Solucionar notificaciones mail automaticas enginyersbcn [Pilar Marinas]

0.104 (2021-04-12)
------------------

* Translate types notify mail [Pilar Marinas]
* Types notify mail [Pilar Marinas]
* Traducciones [Pilar Marinas]
* Optimizar codigo funcion ram cache [Pilar Marinas]
* Quitar cache no funciona [Pilar Marinas]
* Cache paquetes instalados [Pilar Marinas]

0.103 (2021-03-25)
------------------

* Traducciones [Pilar Marinas]
* Soup Header and Footer [Pilar Marinas]

0.102 (2021-03-08)
------------------

* Traducciones [Pilar Marinas]

0.101 (2021-02-18)
------------------

* Tocador para comunitats [Pilar Marinas]
* Traducciones export_users_communities [Pilar Marinas]
* Traducciones Añadir comunidad como favorita a todos los usuarios [Pilar Marinas]
* Añade a favorito a todos los usuarios inluidos usuarios de grupos subcritos a X comunidad [Pilar Marinas]
* Añadir nueva tarea del cron export_users_communities [Iago López Fernández]

0.100 (2021-02-16)
------------------

* No notificar por mail evento si hay asistentes [Pilar Marinas]

0.99 (2021-02-15)
-----------------

* Add variable type for email notification [Pilar Marinas]

0.98 (2021-02-11)
-----------------

* Comentar paquete generali que no esta en PRO [Pilar Marinas]

0.97 (2021-02-11)
-----------------

* Parche para que funcione la creacion de grupos ldap desde usuarios y grupos [Pilar Marinas]
* Traduccion de nuevo portlet ulearn5.zoom [Iago López Fernández]

0.96 (2021-01-27)
-----------------

* Add view future events [Pilar Marinas]
* Cambios migrador para generali [Pilar Marinas]
* Migrador de las puntuaciones de generali generali_scores [Pilar Marinas]

0.95 (2021-01-08)
-----------------

* Quitar notificacion fichero para Provital [Pilar Marinas]

0.94 (2020-11-26)
-----------------

* Reemplazar getToolByName por api.portal.get_tool [Iago López Fernández]
* Reemplazar getToolByName por api.portal.get_tool [Iago López Fernández]

0.93 (2020-11-18)
-----------------

* Fix mails_users_community_black_lists [Iago López Fernández]
* Merge remote-tracking branch 'origin/notificaciones' into develop [pilar.marinas]

0.92 (2020-11-12)
-----------------

* Modificar saveeditacl para que se pueda hacer por puerto necesario url_site en ulearn settings [Pilar Marinas]

0.91 (2020-11-11)
-----------------

* Traducciones etherpad [Iago López Fernández]

0.90 (2020-10-13)
-----------------

* Que el campo mail no se mire para el badget de la foto [Pilar Marinas]
* Add description notify by mail [Pilar Marinas]
* Modificar codigo para el badget de la imagen lo mire del soup y no actualize siempre foto [Pilar Marinas]
* Ampliar variables que se pueden utilizar en los templates de los mensajes [Iago López Fernández]
* Añadir vista addcommunityasfavoritefromallusers [Iago López Fernández]

0.89 (2020-09-29)
-----------------

* api/news url_site [Iago López Fernández]
* Fix url [Iago López Fernández]

0.88 (2020-09-17)
-----------------

* Vista activar etherpad en las comunidades [root]
* Vista que añade en la carpeta documentos de todas las comunidades que se puedan crear documentos etherpad [Pilar Marinas]
* Fix bitly_api_key [Iago López Fernández]

0.87 (2020-09-08)
-----------------

* Delete Nominas Mes [Pilar Marinas]
* Traducciones [Iago López Fernández]
* Modificado workflow para que WebMaster pueda pasar de borrador a intranet [Pilar Marinas]
* Solucionar que no pete al reinstalar paquete ulearn5.core en unite [Pilar Marinas]
* Fix statscsv_view [Iago López Fernández]
* Quitar notificación por correo al crear una imagen [Iago López Fernández]
* Traducción [Iago López Fernández]

0.86 (2020-08-04)
-----------------

* api/links customized for new paysheets [alberto.duran]
* Traduccion portlet [Iago López Fernández]

0.85 (2020-07-24)
-----------------

* Gestionar errores auto_import_from_FTP para cron [Iago López Fernández]
* Cambiar enlace a las nominas de la APP [Iago López Fernández]

0.84 (2020-07-23)
-----------------

* Añadir enlace a las nominas en la APP [Iago López Fernández]

0.83 (2020-07-20)
-----------------

* Solucionar error REGEX bitly [Iago López Fernández]
* select2_maxuser_widget: dar un segundo intento de carga del select2 [Iago López Fernández]

0.82 (2020-07-14)
-----------------

* Remove mail user to mails_users_community_lists in community [Pilar Marinas]

0.81 (2020-07-14)
-----------------

* Guardar mails users si notificar automatic is true [Pilar Marinas]

0.80 (2020-07-10)
-----------------

* Marmoset filter format para que no den error usuarios en grupos Medichem [Pilar Marinas]
* Marmoset filter format para que no den error usuarios en grupos Medichem [Pilar Marinas]
* Para  no de error user no email [Pilar Marinas]
* Para que no pete grupo accento y no de error user no email [Pilar Marinas]
* Para que no de error la suscripcion a comunidad si el usuario no tiene email [Pilar Marinas]

0.79 (2020-07-06)
-----------------

* Solucionar error envio notificacion x mail automatica [Pilar Marinas]

0.78 (2020-07-01)
-----------------

* Solucionar codificacion notificacion mail en outlook [Pilar Marinas]

0.77 (2020-06-30)
-----------------

* Solucionar error notificar x mail [Pilar Marinas]

0.76 (2020-06-29)
-----------------

* Notificar mail [Pilar Marinas]
* Vista notify_manual_in_community para EBCN [Pilar Marinas]
* Vista notify_manual_in_community para EBCN [Pilar Marinas]
* Notificar por email [Iago López Fernández]
* Traducciones [Pilar Marinas]
* Notificacion mail idioma por defecto site si plantilla no definida [Pilar Marinas]
* Plantilla notificacion mail idioma por defecto [Pilar Marinas]
* Notificar por email [Pilar Marinas]

0.75 (2020-06-25)
-----------------

* Configurable comunidad  si quieres ver activityStream o Documents [Pilar Marinas]

0.74 (2020-06-09)
-----------------

* Quitar target=_blank WS noticia porque da error en ios [Pilar Marinas]
* Generar bitly respuesta webservice /api/news/{newid}?absolute_url={absolute_url} [Pilar Marinas]
* Traducción [Iago López Fernández]
* Traducción [Iago López Fernández]

0.73 (2020-04-29)
-----------------

* Traducciones [Pilar Marinas]
* Solucionar notificacion activity stream archivo protegido [Pilar Marinas]
* Corregir error de codificación [Iago López Fernández]
* Hook add protected file when intranet [Pilar Marinas]

0.72 (2020-04-28)
-----------------

* Compartit amb mi si no encuentra obj en el catalogo return False para que no de error [Pilar Marinas]

0.71 (2020-04-27)
-----------------

* Traduccion menu [Iago López Fernández]

0.70 (2020-04-27)
-----------------

* Modify time interval 15 events [Pilar Marinas]
* TRaducciones [Iago López Fernández]
* Modify format time events for user [Pilar Marinas]
* Modificar workflow genweb_intranet para que de privado se pueda pasar a estado intranet [Pilar Marinas]
* View in clouseau to add Protected File in folder documents to Communities [Pilar Marinas]
* Si esta instalado el externalstorage que te muestre en documents de la comunidad archivo protegido [Pilar Marinas]

0.69 (2020-04-20)
-----------------

* Add message hook protected file [Pilar Marinas]

0.68 (2020-04-06)
-----------------

* Traducciones timezone [Pilar Marinas]
* Solucionar que evento se guarde en la hora de la timezone seleccionada [Pilar Marinas]
* Add timezone user in event if not selected [Pilar Marinas]
* Solucionar que guarde el evento con la timezone seleccionada [Pilar Marinas]

0.67 (2020-03-20)
-----------------

* Añadir timezone a las ocurrencias de los eventos [Iago López Fernández]
* Añadir timezone a las ocurrencias de los eventos [Iago López Fernández]
* Quitar ipdb [Iago López Fernández]
* Arreglar error timezone pytz [Iago López Fernández]
* Utils -> Portlet calendar: tener en cuenta los timezone [Iago López Fernández]
* Añadir timezone en los eventos [Iago López Fernández]
* Ver evento con la timezone del usuario [Iago López Fernández]
* Añadir timezone en la preferencias personales [Iago López Fernández]

0.66 (2020-03-09)
-----------------

* Traducción hook documento [Iago López Fernández]

0.65 (2020-03-03)
-----------------

* New WS api/people/users [pilar.marinas]
* Solucionar error elastic si comparten y no es comunidad [pilar.marinas]

0.64 (2020-02-17)
-----------------

* Preparing release 0.63 [pilar.marinas]
* Afegir usuaris generics enginyersbcn [pilar.marinas]

0.63 (2020-02-17)
-----------------

* Afegir usuaris generics enginyersbcn [pilar.marinas]

0.62 (2020-02-14)
-----------------

* Modificado get_roles para que funcione la subscripcion usuarios si usuari pertene a un grupo [Iago López Fernández]
* Modificado get_roles para que funcione la subscripcion usuarios si usuari pertene a un grupo [pilar.marinas]

0.61 (2020-02-12)
-----------------

* Add users enginyersBCN [pilar.marinas]
* Cambio literal: ver todas a ver todos [Iago López Fernández]
* Cambiar propiedad typesUseViewActionInListings a ulearn.video\nVideo\nImage [Iago López Fernández]

0.60 (2020-02-11)
-----------------

* Closeau: añadir addallcommunitiesasfavoritefromallusers [Iago López Fernández]

0.59 (2020-02-04)
-----------------

* Literal portlet thinnkers [Iago López Fernández]
* Literal portlet thinnkers [Iago López Fernández]

0.58 (2020-01-16)
-----------------

* Añadir usuario sac en los usuarios validos de authenticateCredentials [Iago López Fernández]

0.57 (2020-01-14)
-----------------

* Modificar compartit amb mi elastic [pilar.marinas]
* Modificar compartit amb mi elastic [pilar.marinas]

0.56 (2019-12-18)
-----------------

* WS api/news/newid [pilar.marinas]
* Traduccion [Iago López Fernández]
* Traducciones evento [Iago López Fernández]

0.55 (2019-12-16)
-----------------

* Eliminar fuzzy locales [Iago López Fernández]

0.54 (2019-12-12)
-----------------

* Invertir resultados de la colección aggregator [Iago López Fernández]

0.53 (2019-12-12)
-----------------

* Añadir usuario dega en los usuarios validos de authenticateCredentials [Iago López Fernández]
* Traduccion [Iago López Fernández]
* Añadir portlet mycommunities en controlportlets + Traducciones [Iago López Fernández]
* Add path in api groups communities [pilar.marinas]
* people_literal: Añadir opción Quién es quién [Iago López Fernández]
* Subscribednews: Solucionar error búsquedas guardadas con acentos [Iago López Fernández]

0.52 (2019-11-14)
-----------------

* Ordenar comunidades en la APP [pilar.marinas]
* Add portal_url in ++ [pilar.marinas]
* Traducciones en el modal de cambio de workflow de la vista folder_contents [Iago López Fernández]

0.51 (2019-11-06)
-----------------

* max_portrait_widget: Arreglar error username [root]
* max_portrait_widget: Arreglar error username [root]
* Ordenar vista comunidades por Organizativas, Cerradas, Abiertas y en orden alfabetico [pilar.marinas]
* max_portrait_widget: Arreglar error username [Iago López Fernández]
* max_portrait_display: Coger imagen del max [Iago López Fernández]

0.50 (2019-10-24)
-----------------

* Traducciones [Iago López Fernández]

0.49 (2019-10-24)
-----------------

* Notificacion Push Noticia cuando se publique en la intranet [pilar.marinas]
* Livesearch: Mostrar 4 resultados y reducir descripción a 140 caracteres [Iago López Fernández]
* Merge remote-tracking branch 'origin/searchusers' into develop [Iago López Fernández]
* Mejora de velocidad searchuser [Iago López Fernández]
* Solucionar error switchmed profile [pilar.marinas]

0.48 (2019-10-02)
-----------------

* Add permission WebMaster to manage users [pilar.marinas]

0.47 (2019-09-20)
-----------------

* Permisos Editor Comunidad revisados [alberto.duran]
* changePermissionsToContent [Iago López Fernández]
* Permisos Editor Comunidad [pilar.marinas]

0.46 (2019-09-17)
-----------------

* Permitir a la API modificar grupos para añadir y eliminar usuarios [Iago López Fernández]

0.45 (2019-09-16)
-----------------

* Añadir paquete plone.restapi [Iago López Fernández]
* Modify literal help portrait [pilar.marinas]

0.44 (2019-09-09)
-----------------

* Traducción error Twitter username [Iago López Fernández]
* Migración por path [Iago López Fernández]
* Mejora migracion de la documentacion de las comunidades [root]

0.43 (2019-07-29)
-----------------

* isValidTwitterUsername [pilar.marinas]

0.42 (2019-07-22)
-----------------

* Ldap group creation parametre [Vicente Iranzo Maestre]
* Varnish in object Modified [pilar.marinas]

0.41 (2019-07-17)
-----------------

* Añadir nuevo widget Fieldset h5 [Iago López Fernández]
* enumerateUsers -> Comprobar que este instalado el paquete base5.core [Iago López Fernández]

0.40 (2019-06-26)
-----------------

* Activar visibilidad Historial [Iago López Fernández]
* Modificar template widget select_multiple_display [Iago López Fernández]
* Widget checkbox info DISPLAY_MODE [Iago López Fernández]
* Widget checkbox info [Iago López Fernández]

0.39 (2019-05-17)
-----------------

* Log get to appconfig for mobile access [Pilar Marinas]
* Travis [Pilar Marinas]

0.38 (2019-05-15)
-----------------

* Solucionar si no hay username gebropharma [Pilar Marinas]
* travsi [Pilar Marinas]
* Marmoset: Aceptar imagenes en data:text/html;base64,... [Iago López Fernández]
* migrationDocumentsCommunities por partes para que no de ClientDisconnected [Pilar Marinas]
* Marmoset: Aceptar imagenes en data:text/html;base64,... [Iago López Fernández]
* Resolver hash comunidades al hacer clear and rebuild por puerto [Pilar Marinas]

0.37 (2019-05-03)
-----------------

* Quitar require collective.easyform [Pilar Marinas]

0.36 (2019-05-02)
-----------------

* Travis [Pilar Marinas]
* Quitar delete_local_roles de la base y anadir usuario en soup [Pilar Marinas]
* Política de privacidad + Traducciones [Iago López Fernández]
* /api/people/{username}/all [Iago López Fernández]
* Merge remote-tracking branch 'origin/estadistiques' into develop [Pilar Marinas]
* Mejorar filtros site y news [Pilar Marinas]
* Mejora buscador subscribednews [Iago López Fernández]
* Vista stats/pageviews: Añadir nuevos path para fitrar [Iago López Fernández]
* Vista stats/pageviews: Solucion fechas [Iago López Fernández]
* Añadir collective.easyform [Iago López Fernández]

0.35 (2019-04-08)
-----------------

* Corregir Estadisticas  path comunidad con mountpoint [Pilar Marinas]

0.34 (2019-04-08)
-----------------

* Mejorar vista /stats/pageviews [Iago López Fernández]
* travis_wait to resolve timeout coverage [Pilar Marinas]

0.33 (2019-04-04)
-----------------

* Mofify test_community_subscribe_post [Pilar Marinas]
* AuthenticatedUsers in OpenCommunity [Pilar Marinas]
* Api GET community [Pilar Marinas]
* Add role Api in WS communities [Pilar Marinas]
* AuthenticatedUsers in OpenCommunity [Iago López Fernández]
* AuthenticatedUsers in OpenCommunity [Pilar Marinas]

0.32 (2019-04-01)
-----------------

* thumbnail_image to image community [Pilar Marinas]

0.31 (2019-04-01)
-----------------

* Solucionar test [Pilar Marinas]

0.30 (2019-04-01)
-----------------

* Clouseau changepermissionstocontent: Quitar permisos de AuthenticatedUsers a las comunidades [Iago López Fernández]
* Modificar permisos comunidades Abiertas [Iago López Fernández]
* Solucionar migracion si plone 4 y 5 misma maquina [Pilar Marinas]
* Clouseau: changePermissionsToContent [Iago López Fernández]
* coverage [Pilar Marinas]
* Traducciones [Iago López Fernández]

0.29 (2019-03-25)
-----------------

* solucionar merge [Pilar Marinas]
* Merge estadistiques [Pilar Marinas]
* Quitar filtro fecha [Pilar Marinas]
* travis [Pilar Marinas]
* travis [Pilar Marinas]
* travis [Pilar Marinas]
* travis [pmarinas]
* Solucionar Travis [pmarinas]
* Solucionar tests [Pilar Marinas]
* Travis [Pilar Marinas]

0.28 (2019-03-18)
-----------------

* Revision permisos webmaster [Pilar Marinas]

0.27 (2019-03-06)
-----------------

* Add Products PloneKeywordManager [Pilar Marinas]
* Cambiar funcion para que si no hay avatar ponga el defaultUser [Pilar Marinas]
* Normalize thumbnail_image [Iago López Fernández]
* Parche para que no mire si el password en LDAP es correcto para enginyersbcn excepto usuarios LDAP [Pilar Marinas]

0.26 (2019-03-04)
-----------------

* Parche para que no mire si el password en LDAP es correcto para enginyersbcn [Pilar Marinas]
* Modificar workflow por defecto (Default) de File y Image [Iago López Fernández]
* GET api/people/{username}: obtener solo los campos publicos [Iago López Fernández]
* Añadir logger al borrar usuario [Iago López Fernández]
* api/people comprobar si el usuario existe en el ldap [Iago López Fernández]

0.25 (2019-02-21)
-----------------

* No notificar events en el activity de abacus [Pilar Marinas]
* Añadir nueva vista get_info_cron_tasks [Iago López Fernández]
* Cambiar permisos para visualizar /ulearn-controlpanel [Iago López Fernández]

0.24 (2019-02-11)
-----------------

* print to logger.info [Iago López Fernández]
* Cambiar vista por defecto de la carpeta eventos de las comunidades al crearlas [grid_events_view] [Iago López Fernández]
* Traducciones [Pilar Marinas]
* Hacer parametrizable la vista migrationfixfolderviews [Iago López Fernández]
* Añadir vista de eventos en las carpetas [Iago López Fernández]
* Clouseau: Formato documentación [Iago López Fernández]
* Añadir vista clouseau: listcontentslocalrolesblock [Iago López Fernández]
* Traducción vista grid_events_view [Iago López Fernández]
* Eliminar vista tot el contingut de carpetes i afegir vista esdeveniments [alberto.duran]
* mispelled [Roberto Diaz]
* Fix portrait widget [Iago López Fernández]
* Mejora vista search del portlet Thinkers [Iago López Fernández]

0.23 (2019-01-31)
-----------------

* Execute cron task [Pilar Marinas]
* Cron task [Pilar Marinas]
* Traduccion [Iago López Fernández]
* Traducciones [Iago López Fernández]

0.22 (2019-01-28)
-----------------

* Add decode UTF-8 en los campos del perfil [Pilar Marinas]
* Fix migrationFixFolderViews [Iago López Fernández]

0.21 (2019-01-24)
-----------------

* Add migrationFixFolderViews + pep8 [Iago López Fernández]
* Poder seleccionar dia de la semana con el que se comienza en los calendarios de los campos de formulario de tipo fecha (Marmoset) [Iago López Fernández]

0.20 (2019-01-15)
-----------------

* changed nomina translation [Roberto Diaz]
* Migration Flash Important APP [Pilar Marinas]
* Migration Flash Important APP [Pilar Marinas]

0.19 (2018-12-20)
-----------------

* Title Site [Pilar Marinas]
* Para que los hooks no den error al crear instancia [Pilar Marinas]

0.18 (2018-12-11)
-----------------

* Add in log objects added and modified [Pilar Marinas]
* Estilos widget multiple [Iago López Fernández]
* Widgets fieldset + multiple [Iago López Fernández]
* Quitar plone_log [Pilar Marinas]
* Traducciones [Iago López Fernández]
* Vista image-portlet-view [Iago López Fernández]
* Remplazar plone_log con logger.info [Pilar Marinas]
* Controlpanel: añadir url_forget_password [Iago López Fernández]
* migrationFlashImportantAPP [Pilar Marinas]
* Solucion error util isInstalledProduct [Iago López Fernández]
* setuphandlers: Permisos para añadir etiquetas [Iago López Fernández]
* setuphandlers: Configuración tiny [Iago López Fernández]
* Añadir util isInstalledProduct [Iago López Fernández]
* Traducciones nominas [Iago López Fernández]

0.17 (2018-11-27)
-----------------

* Neteja portlets per comunitats Plone 5 [Pilar Marinas]
* Delete setup include in migration4to5 [Pilar Marinas]

0.16 (2018-11-26)
-----------------

* Merge [Pilar Marinas]
* Migrate portal_role_manager and modify clouseau [Pilar Marinas]
* Controlpanel default language ca [Pilar Marinas]
* Universal link: Añadir condicion borrada [Iago López Fernández]
* migrationPath [Pilar Marinas]
* MigrationUsersProfiles [Pilar Marinas]

0.15 (2018-11-16)
-----------------

* Add pytz requirement [alberto.duran]

0.14 (2018-11-16)
-----------------

* Afegir Popen [alberto.duran]
* migrationEventsCommunities [Pilar Marinas]
* Migracion favoritedBy y modificar formulario para poner los path del export de Plone 4 y 5 [Pilar Marinas]

0.13 (2018-11-13)
-----------------

* Deshacer: Class Object universal link dentro de las comunidades [Iago López Fernández]

0.12 (2018-11-12)
-----------------

* Class Object universal link dentro de las comunidades [Iago López Fernández]
* Object universal link - no verlo en la página principal [Iago López Fernández]
* Object universal link [Iago López Fernández]

0.11 (2018-11-08)
-----------------

* Modificar ruta migrationDocumentsCommunities [Pilar Marinas]
* Solucion widget select2_maxuser_widget [iago.lopez]
* ExecuteCronTasks [Pilar Marinas]
* Searchuser: no ver usuarios de la lista nonvisible [iago.lopez]

0.10 (2018-10-30)
-----------------

* Solucionar test [Pilar Marinas]
* Si no hay url y check no hacer el elastic [Pilar Marinas]

0.9 (2018-10-29)
----------------

* Traducción portlet quicklinks [iago.lopez]
* Que no aparezcan los terminos de uso si no hay url en ulearn settings [Pilar Marinas]
* Avance vista execute_cron_tasks [iago.lopez]
* Quitar Genweb [Pilar Marinas]
* Add API saveeditacl [Pilar Marinas]
* api/news: mostrar tambien noticias de comunidades [iago.lopez]
* api/people/{username}: Permitir el cambio de email [iago.lopez]
* Viewlet ulearn.newstoolbar arreglar funcionamiento flashes informativos [iago.lopez]
* Only Site Administrator permission Delete_objects_Permission in frontpage, gestion, documents [Pilar Marinas]
* mrs5.max [Pilar Marinas]
* Add domain in successful login [Pilar Marinas]

0.8 (2018-10-11)
----------------

* Cambiar condicion isPortletListActivate [iago.lopez]
* Traducciones [iago.lopez]
* Solucionar error ImportFileToFolder [Pilar Marinas]
* Merge externs [Pilar Marinas]
* Solucionar app i migracio [Pilar Marinas]
* Solucionar api news plone5 [root]
* Comentar hooks - Notificación de modificación: Documento y Evento [iago.lopez]
* Añadir nueva vista a colección aggregator [iago.lopez]
* Delete Userschema in core [Pilar Marinas]
* Update viewuserswithnotupdatedphoto [iago.lopez]
* Portlet Quicklinks [iago.lopez]
* Widget Visibilitdad: Cambiar interfaces [iago.lopez]
* Traduccion + Esconder Configuración del Sitio del menú (Actions) [iago.lopez]
* Visibilidad campos del perfil [iago.lopez]
* API: Renovar extender_name [iago.lopez]
* Eliminar residuos del portlet eConnect [iago.lopez]
* Traducciones [iago.lopez]
* Tipo de contenido Bàner + Portlet Bàners [iago.lopez]
* Traducción [iago.lopez]
* Portlet Ulearn RSS + Traducciones [iago.lopez]
* Traducciones [iago.lopez]
* Modificar terminos uso comunidades [Pilar Marinas]
* Define defaults colors of site [Pilar Marinas]
* Terminos de uso (Falta ++add++ulearn.community) [iago.lopez]
* Traducciones [iago.lopez]
* added CMYK support to profile images [Pilar Marinas]
* Limpieza [iago.lopez]
* Añadir campos nuevos a la comunidad (show_news - show_events) [iago.lopez]
* Traducciones [iago.lopez]
* Notificar noticia en la actividad [iago.lopez]
* Quitar fuzzy [iago.lopez]
* Portlet Smart [iago.lopez]
* Portlet Smart [iago.lopez]
* WS Modify displayName user for uTalk [Pilar Marinas]

0.7 (2018-07-05)
----------------

* Modify hooks community remove [Pilar Marinas]

0.6 (2018-07-03)
----------------

* Terminos de uso [iago.lopez]
* update viewlets for news item [root@comunitatsdevel]
* update colection criteria with draft state [alberto.duran]
* traduccions [alberto.duran]
* traduccions [alberto.duran]
* add description for addable types [alberto.duran]
* traduccions [alberto.duran]
* traduccions [alberto.duran]
* Modify portal_type ulearn5.owncloud.file_owncloud by CloudFile [Pilar Marinas]
* traduccions [alberto.duran]
* update migrator communities [alberto.duran]
* Traduucciones [iago.lopez]
* add missing template for migration [alberto.duran]
* migrationDocumentsCommunity [alberto.duran]
* Posibilitat de migrar nomes una o varies comunitats [Pilar Marinas]
* Vista migracion comunidades de plone 4 a 5 [Pilar Marinas]
* Traduccions [alberto.duran]
* Traduccions [alberto.duran]
* Checkbox comunitat obligatori amb missatge plone [alberto.duran]

0.5 (2018-06-07)
----------------

* multiple changes based on IE11 [Roberto Diaz]
* Modify elastic_index [Pilar Marinas]
* Merge branch 'master' of github.com:UPCnet/ulearn5.core [Pilar Marinas]
* Solucionar elastic + añadir los patches del ulearn.patches [Pilar Marinas]
* added persons translations [Roberto Diaz]
* View for update permissions [alberto.duran]

0.4 (2018-05-31)
----------------

* Añadir vista clouseau para eliminar foto de un usuario [Pilar Marinas]
* Envia solo carpetas de primer nivel y enlaces [Pilar Marinas]

0.3 (2018-05-29)
----------------

* Added ping view [alberto.duran]

0.2 (2018-05-23)
----------------

* Migration to independent package for osiris5 [alberto.duran]

0.1 (2018-05-22)
----------------

- Initial release.
  [pilar.marinas@upcnet.es]
