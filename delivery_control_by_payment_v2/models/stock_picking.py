# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _check_direct_customer_payment(self):
        """
        Prevent validating delivery before invoice payment
        """

        for picking in self:

            if picking.picking_type_code != "outgoing":
                continue

            sale = picking.sale_id

            if not sale:
                continue

            if sale.partner_id.customer_type != "direct":
                continue

            invoices = sale.invoice_ids.filtered(
                lambda inv:
                inv.move_type == "out_invoice"
                and inv.state == "posted"
            )

            if not invoices:
                raise UserError(_(
                    "Customer invoice must be created first."
                ))

            unpaid = invoices.filtered(
                lambda inv: inv.payment_state != "paid"
            )

            if unpaid:
                raise UserError(_(
                    "Delivery is blocked.\n\n"
                    "Customer is Direct and invoice has not been paid."
                ))

    def button_validate(self):

        self._check_direct_customer_payment()

        return super().button_validate()