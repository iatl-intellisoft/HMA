# -*- coding: utf-8 -*-
{
    'name': 'Stock Lot Volume (CBM)',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Track lot volume (CBM) on move lines and use it in landed cost distribution',
    'description': """
        - Adds Volume (CBM) field on stock.move.line (visible only for lot-tracked products)
        - Automatically reflects move line volume to the product lot
        - Adds Total CBM field on stock.picking (sum of all move line volumes)
        - Adds "By Lot Volume" split method in landed costs
    """,
    'depends': ['stock', 'stock_landed_costs'],
    'data': [
        'views/stock_move_line_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_landed_cost_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
