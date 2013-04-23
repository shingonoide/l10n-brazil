{
    "name": "Server manager",
    "version": "1.0",
    "author": "Danimar Ribeiro",
    "category": "Tools",
    "description": """
        Este módulo permite configurar os dominios e os bancos de dados automaticamente.
        Necessita da api para o Zerigo DNS:
        https://bitbucket.org/petersanchez/zerigodns
    """,
    'depends': [
        'base',
        'auth_signup',
    ],
    "init_xml": [],
    'update_xml': ["server_manager_view.xml", "customer_manager_view.xml"],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'qweb': ['static/src/xml/auth_signup.xml'],
    'bootstrap': True,
}