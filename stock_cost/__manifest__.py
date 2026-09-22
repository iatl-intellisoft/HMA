# -*- coding: utf-8 -*-
##############################################################################
#
#    IATL International, OpenERP Partner
#    Copyright (C) 2019 IATL.
#
##############################################################################

{
    'name': "WMS With Foreign Currency",
    'version': "0.1",
    'sequence': 1,
    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'license': "AGPL-3",
    'category': "Hidden",
    'description': """
WMS With Foreign Currency
=====================

This module show the stock value of product in foreign currency
 
""",
    'depends': ['stock_account','product'],
    'data': [
        'security/ir.model.access.csv',
        'security/stock_cost_security.xml',
        'wizard/stock_valuation_layer_revaluation_views.xml',
        'views/product_template_view.xml',
        'views/stock_view.xml',
        'views/stock_change_cost_view.xml',
        'wizard/stock_change_standard_price_views.xml'
        # # 'views/hr_academic_view.xml',
        # # 'views/hr_certification_view.xml',
        # # 'views/hr_employee_view.xml',
        # # 'views/hr_professional_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    
}
