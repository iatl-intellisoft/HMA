# -*- coding: utf-8 -*-
{
    'name': "Check Managment",

    'summary': """
        Manage Your Check Follow Up""",

    'description': """
        
    """,

    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Accounting',
    'version': '18.0',
    'depends': ['account','check_printing_custom'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/res_config_settings_view.xml',
    ],

   
}
