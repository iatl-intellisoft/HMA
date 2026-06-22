# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    volume = fields.Float(
        'Volume (CBM)',
        digits='Volume',
        help="Volume in cubic meters (CBM) for this move line's lot.",
    )
