# -*- coding: utf-8 -*-
{
    'name': "HR Custom",

    'summary': """
        """,

    'description': """
        
    """,

    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Human Resource',
    'version': '18.0',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_views.xml',
        'views/res_config_settings.xml',
    ],
}
