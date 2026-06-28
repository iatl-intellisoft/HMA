# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_qty_available = fields.Float(
        string='On Hand',
        related='product_id.qty_available',
        digits='Product Unit of Measure',
        help="Current on-hand quantity of the product.",
    )
