{
    'name': 'Account Payment Split Access',
    'version': '18.0.1.0.0',
    'summary': 'Split payment menus: Cash/Bank × Customer/Vendor with access control',
    'category': 'Accounting/Accounting',
    'author': 'Custom',
    'depends': ['account'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/account_payment_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
