# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOpsReportLine(models.TransientModel):
    _name = 'sale.ops.report.line'
    _description = 'Operations Report Line'
    _order = 'partner_id asc, sale_order_ref asc, id asc'

    wizard_id = fields.Many2one(
        'sale.ops.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    picking_id = fields.Many2one('stock.picking', string='Delivery', readonly=True)

    # ── Report columns ────────────────────────────────────────────────────────
    partner_id = fields.Many2one('res.partner', string='Customer Name', readonly=True)
    sale_order_ref = fields.Char(string='SO Ref', readonly=True)
    demand = fields.Float(string='Demand', digits='Product Unit of Measure', readonly=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', readonly=True)
