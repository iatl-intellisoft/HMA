# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_qty_available = fields.Float(
        string='On Hand',
        compute='_compute_product_qty_available',
        digits='Product Unit of Measure',
        help="Current on-hand quantity of the product at the selected location.",
    )

    @api.depends('product_id', 'warehouse_id')
    def _compute_product_qty_available(self):
        for line in self:
            if not line.product_id:
                line.product_qty_available = 0.0
                continue
            location = line.warehouse_id.lot_stock_id if line.warehouse_id else False
            if location:
                line.product_qty_available = line.product_id.with_context(
                    location=location.id
                ).qty_available
            else:
                line.product_qty_available = line.product_id.qty_available
