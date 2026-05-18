# -*- coding: utf-8 -*-
{
    'name': "HR Department Custom",

    'summary': """
        """,

    'description': """
    """,

    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Human Resources',
    'depends': ['hr', 'analytic'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_views.xml',
        'views/res_user_view.xml',
    ],
}