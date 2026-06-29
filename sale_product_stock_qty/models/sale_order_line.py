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
    warehouse_stock_display = fields.Char(
        string='On Hand',
        compute='_compute_product_qty_available',
        help="Warehouse and on-hand quantity at that warehouse's stock location.",
    )

    @api.depends('product_id', 'warehouse_id')
    def _compute_product_qty_available(self):
        for line in self:
            if not line.product_id:
                line.product_qty_available = 0.0
                line.warehouse_stock_display = ''
                continue
            location = line.warehouse_id.lot_stock_id if line.warehouse_id else False
            if location:
                qty = line.product_id.with_context(location=location.id).qty_available
                line.product_qty_available = qty
                line.warehouse_stock_display = '%s - %g' % (line.warehouse_id.name, qty)
            else:
                qty = line.product_id.qty_available
                line.product_qty_available = qty
                line.warehouse_stock_display = '%g' % qty
