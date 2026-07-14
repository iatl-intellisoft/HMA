# -*- coding: utf-8 -*-

from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    proximity_type = fields.Selection(
        selection=[
            ('near', 'Near'),
            ('far', 'Far'),
        ],
        string='Proximity',
        default='near',
        required=True,
        help="Used to split the printed Operations Report into two "
             "sections: nearby warehouses vs. far warehouses.",
    )
