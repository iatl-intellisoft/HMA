# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from itertools import groupby


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=False,
    )

    @api.depends('route_id', 'order_id.warehouse_id', 'product_packaging_id', 'product_id')
    def _compute_warehouse_id(self):
        """Override to preserve manually set warehouses on existing lines.

        The standard compute always overwrites warehouse_id from the order or route.
        This override skips recomputation for saved lines that already have a warehouse
        assigned, so that per-line warehouse selections survive dependency changes
        (e.g. product changes, order confirmation, etc.).
        """
        lines_to_compute = self.filtered(lambda l: not l.id or not l.warehouse_id)
        lines_to_preserve = self - lines_to_compute

        # Explicitly write the current DB value back into the cache so Odoo
        # does not treat the field as "unset" for these lines after the compute.
        for line in lines_to_preserve:
            line.warehouse_id = line.warehouse_id

        super(SaleOrderLine, lines_to_compute)._compute_warehouse_id()

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
            wh.display_name = '%s - %g qty' % (wh.name, qty)
