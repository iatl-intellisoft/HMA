# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_under_manufacturing = fields.Float(
        string='Qty Under Manufacturing',
        compute='_compute_custom_picking_qtys',
        store=False,
        digits='Product Unit of Measure',
        help='Quantity from related receipts currently Under Manufacturing.',
    )

    qty_under_shipping = fields.Float(
        string='Qty Under Shipping',
        compute='_compute_custom_picking_qtys',
        store=False,
        digits='Product Unit of Measure',
        help='Quantity from related receipts currently Under Shipping.',
    )

    def _compute_custom_picking_qtys(self):
        for line in self:
            qty_manufacturing = 0.0
            qty_shipping = 0.0

            if not line.order_id or not line.product_id:
                line.qty_under_manufacturing = 0.0
                line.qty_under_shipping = 0.0
                continue

            # Find the correct column name for purchase link in stock_move
            self.env.cr.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'stock_move' 
                AND column_name LIKE '%purchase%'
            """)
            cols = [r[0] for r in self.env.cr.fetchall()]

            # Get all receipt pickings for this PO via group by on move level
            self.env.cr.execute("""
                SELECT DISTINCT sm.picking_id, sp.custom_state, SUM(sm.product_qty) as qty
                FROM stock_move sm
                JOIN stock_picking sp ON sm.picking_id = sp.id
                JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                WHERE sm.product_id = %s
                AND sp.state NOT IN ('cancel', 'done')
                AND sm.state NOT IN ('cancel', 'done')
                AND spt.code = 'incoming'
                AND sp.id IN (
                    SELECT DISTINCT picking_id
                    FROM stock_move
                    WHERE product_id = %s
                        AND origin ILIKE %s
                )
                GROUP BY sm.picking_id, sp.custom_state
            """, (line.product_id.id, line.product_id.id, '%' + (line.order_id.name or '') + '%'))

            for row in self.env.cr.fetchall():
                cs = row[1]
                qty = row[2] or 0.0
                if cs == 'under_manufacturing':
                    qty_manufacturing += qty
                elif cs == 'under_shipping':
                    qty_shipping += qty

            line.qty_under_manufacturing = qty_manufacturing
            line.qty_under_shipping = qty_shipping