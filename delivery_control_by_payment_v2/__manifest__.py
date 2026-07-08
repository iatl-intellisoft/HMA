{
    'name': 'Delivery Control By Payment',
    'version': '18.0.1.0.0',
    'summary': 'العميل المباشر: لا يتم التوصيل إلا بعد الدفع. العميل المعتمد: يتم التوصيل مباشرة بعد اعتماد المسؤول',
    'category': 'Inventory/Sales',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    "depends": [
        "sale_management",
        "stock",
        "account",
    ],
    'data': [
        
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
