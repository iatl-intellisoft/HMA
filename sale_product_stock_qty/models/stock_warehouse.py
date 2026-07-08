# -*- coding: utf-8 -*-
from odoo import api, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.depends('name', 'code')
    def _compute_display_name(self):
        product_id = self.env.context.get('sale_line_product_id')
        if not product_id:
            return super()._compute_display_name()
        product = self.env['product.product'].browse(product_id)
        for wh in self:
            qty = product.with_context(location=wh.lot_stock_id.id).free_qty
            wh.display_name = '%s — %g available' % (wh.name, qty)
