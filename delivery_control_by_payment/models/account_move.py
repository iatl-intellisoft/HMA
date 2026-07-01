# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_payment_state(self):
        res = super()._compute_payment_state()
        for move in self:
            if (
                move.move_type == 'out_invoice'
                and move.payment_state in ('partial', 'paid', 'in_payment')
            ):
                move._release_direct_customer_deliveries()
        return res

    def _release_direct_customer_deliveries(self): 
        for move in self:
            orders = move.invoice_line_ids.sale_line_ids.order_id
            orders = orders.filtered(lambda o: o.state == 'pending_payment')
            orders._release_blocked_delivery()
