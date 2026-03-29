{
    'name': 'sales order custom',
    'version': '1.0.0',
    'summary': 'sales order custom',
    'author': "IATL-Intelloft",
    'depends': ['sale_management','stock'],
    
    'data': [ 
        'security/ir.model.access.csv',
        'views/sale_order_inh_views.xml', 
    ],
    'license': 'OPL-1',

    'application': False,
}