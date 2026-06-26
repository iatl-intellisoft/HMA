# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    total_demand_qty = fields.Float(
        'Total Quantity',
        compute='_compute_total_demand_qty',
        store=True,
        digits='Product Unit of Measure',
        help="Sum of all product demand quantities on this delivery.",
    )

    @api.depends('move_ids.product_uom_qty', 'move_ids.state')
    def _compute_total_demand_qty(self):
        for picking in self:
            picking.total_demand_qty = sum(
                picking.move_ids.filtered(
                    lambda m: m.state != 'cancel'
                ).mapped('product_uom_qty')
            )
