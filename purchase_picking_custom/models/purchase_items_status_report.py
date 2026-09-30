# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseItemsStatusReport(models.Model):
    """Read-only reporting model: one row per product, summarizing the
    quantity currently sitting at each stage of the shipment/import
    pipeline based on its related incoming stock pickings (SQL view, see
    _table_query).

    - Under Preparation -> pickings with custom_state = 'under_manufacturing'
    - In Transit         -> pickings with custom_state = 'under_shipping'
    - Under Clearance    -> pickings with custom_state = 'under_clearance'
    - Stock              -> pickings in the real 'done' state (i.e.
                             received quantity)

    custom_state is a pure tracking overlay (see stock_picking.py); the
    real 'state' field is only ever used here for the 'done' (received)
    bucket, since that one is a genuine standard workflow state.
    """
    _name = 'purchase.items.status.report'
    _description = 'Items Status Report'
    _auto = False
    _order = 'sequence'

    sequence = fields.Integer(string='No.', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    under_preparation_qty = fields.Float(string='Under Preparation', readonly=True)
    in_transit_qty = fields.Float(string='In Transit', readonly=True)
    under_clearance_qty = fields.Float(string='Under Clearance', readonly=True)
    stock_qty = fields.Float(
        string='Stock',
        readonly=True,
        help='Received quantity (from incoming receipts already validated/done).',
    )

    @property
    def _table_query(self):
        return """
            SELECT
                pp.id AS id,
                ROW_NUMBER() OVER (ORDER BY pt.name) AS sequence,
                pp.id AS product_id,
                COALESCE(SUM(CASE WHEN sp.custom_state = 'under_manufacturing' THEN sm.quantity ELSE 0 END), 0) AS under_preparation_qty,
                COALESCE(SUM(CASE WHEN sp.custom_state = 'under_shipping' THEN sm.quantity ELSE 0 END), 0) AS in_transit_qty,
                COALESCE(SUM(CASE WHEN sp.custom_state = 'under_clearance' THEN sm.quantity ELSE 0 END), 0) AS under_clearance_qty,
                COALESCE(SUM(CASE WHEN sp.state = 'done' THEN sm.quantity ELSE 0 END), 0) AS stock_qty
            FROM stock_move sm
            JOIN stock_picking sp ON sp.id = sm.picking_id
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            JOIN product_product pp ON pp.id = sm.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE spt.code = 'incoming'
              AND sm.state != 'cancel'
              AND sp.state != 'cancel'
            GROUP BY pp.id, pt.name
        """
