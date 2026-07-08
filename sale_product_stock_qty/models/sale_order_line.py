# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_qty_available = fields.Float(
        string='Available',
        compute='_compute_product_qty_available',
        digits='Product Unit of Measure',
        help="Real-time available quantity (on-hand minus reserved) at the selected warehouse.",
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
                ).free_qty
            else:
                line.product_qty_available = line.product_id.free_qty
