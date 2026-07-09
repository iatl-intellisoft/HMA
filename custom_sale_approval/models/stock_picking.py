# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _check_customer_payment(self):
        for picking in self:

            if picking.picking_type_code != "outgoing":
                continue

            sale = picking.sale_id
            if not sale:
                continue

            partner = sale.partner_id

            if partner.requires_sale_approval not in (0, False):
                continue

            invoices = sale.invoice_ids.filtered(
                lambda inv: inv.move_type == "out_invoice"
                and inv.state == "posted"
            )

            if not invoices:
                raise UserError(_(
                    "You must create and post the customer invoice before validating the delivery."
                ))

            unpaid = invoices.filtered(
                lambda inv: inv.amount_residual > 0
            )

            if unpaid:
                raise UserError(_(
                    "Delivery cannot be validated.\n\n"
                    "The customer invoice must be fully paid before confirming the delivery."
                ))

    def button_validate(self):
        self._check_customer_payment()
        return super().button_validate()
