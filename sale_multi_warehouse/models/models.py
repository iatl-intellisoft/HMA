# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from itertools import groupby


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one('stock.warehouse', readonly=False)

    def _prepare_procurement_values(self, group_id):
        res = super()._prepare_procurement_values(group_id=group_id)
        res.update({"warehouse_id": self.warehouse_id})

        return res

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.depends('name', 'code')
    def _compute_display_name(self):
        product_id = self.env.context.get('sale_line_product_id')
        if not product_id:
            return super()._compute_display_name()
        product = self.env['product.product'].browse(product_id)
        for wh in self:
            qty = product.with_context(location=wh.lot_stock_id.id).qty_available
            wh.display_name = '%s - %g Qty' % (wh.name, qty)
