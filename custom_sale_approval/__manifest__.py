# -*- coding: utf-8 -*-
{
    'name': 'اعتماد طلبات المبيعات للعملاء المعتمدين',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'مسار اعتماد إضافي لطلبات البيع الخاصة بالعملاء المباشرين قبل تحويلها إلى أمر بيع',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'stock'],
    'data': [
        'security/sale_approval_security.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
