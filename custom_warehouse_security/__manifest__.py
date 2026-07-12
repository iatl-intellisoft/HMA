{
    'name': 'تقييد صلاحيات أمناء المخازن + طباعة إذن التوصيل مرة واحدة',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'تقييد أمين المخزن على عمليات مخزنه فقط + منع طباعة إذن التوصيل أكثر من مرة',
    'author': 'Custom',
    'depends': ['stock', 'hr'],
    'data': [
        'security/security.xml',
        'views/hr_employee_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
