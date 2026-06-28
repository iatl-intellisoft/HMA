{
    'name': 'Delivery Order Report',
    'version': '18.0.1.0.0', 
    'depends': [
        'base',
        'contacts',
        'stock',
        'sale',
    ],
    'data': [
        'data/delivery_order_report.xml',
        'views/view_partner.xml'
    ],
    'installable': True,
    'application': False,
}
