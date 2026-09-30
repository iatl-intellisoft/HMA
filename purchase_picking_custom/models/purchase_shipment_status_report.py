# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseShipmentStatusReport(models.Model):
    """Read-only reporting model: one row per confirmed Purchase Order,
    summarizing its shipment tracking information (SQL view, see
    _table_query)."""
    _name = 'purchase.shipment.status.report'
    _description = 'Shipments Status Report'
    _auto = False
    _order = 'sequence'

    sequence = fields.Integer(string='No.', readonly=True)
    order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Supplier', readonly=True)
    invoice_number = fields.Char(
        string='Invoice Number',
        readonly=True,
        help='Related vendor bill number(s) for this purchase order.',
    )
    loading_date = fields.Date(string='Loading Date', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    amount_total = fields.Monetary(
        string='Actual Value + Freight',
        readonly=True,
        currency_field='currency_id',
        help='Total value of the purchase order (goods + freight).',
    )
    shipment_date = fields.Date(string='Shipment Date', readonly=True)
    etd = fields.Date(string='ETD', readonly=True)
    eta = fields.Date(string='ETA', readonly=True)
    shipping_line = fields.Char(string='Shipping Line', readonly=True)
    shipment_status = fields.Selection(
        selection=[
            ('under_preparation', 'Under Preparation'),
            ('loaded', 'Loaded'),
            ('in_transit', 'In Transit'),
            ('arrived_at_port', 'Arrived at Port'),
            ('under_clearance', 'Under Clearance'),
            ('received', 'Received'),
        ],
        string='Shipment Status',
        readonly=True,
    )
    free_days = fields.Integer(
        string='Free Days',
        compute='_compute_free_days',
        help='Days remaining between today and the ETA (negative if the ETA has passed).',
    )

    @api.depends('eta')
    def _compute_free_days(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.free_days = (rec.eta - today).days if rec.eta else False

    @property
    def _table_query(self):
        return """
            SELECT
                po.id AS id,
                ROW_NUMBER() OVER (ORDER BY po.id) AS sequence,
                po.id AS order_id,
                po.partner_id AS partner_id,
                po.currency_id AS currency_id,
                po.amount_total AS amount_total,
                po.loading_date AS loading_date,
                po.shipment_date AS shipment_date,
                po.etd AS etd,
                po.eta AS eta,
                po.shipping_line AS shipping_line,
                po.shipment_status AS shipment_status,
                (
                    SELECT string_agg(DISTINCT am.name, ', ')
                    FROM account_move_purchase_order_rel rel
                    JOIN account_move am ON am.id = rel.account_move_id
                    WHERE rel.purchase_order_id = po.id
                      AND am.state != 'cancel'
                ) AS invoice_number
            FROM purchase_order po
            WHERE po.state IN ('purchase', 'done')
        """

    def action_open_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.order_id.id,
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
        }
