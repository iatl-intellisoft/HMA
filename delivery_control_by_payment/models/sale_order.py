# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_completed = fields.Boolean(
        string="Payment Completed",
        compute="_compute_payment_completed",
        store=False,
    )

    payment_warning = fields.Html(
        compute="_compute_payment_completed"
    )

    @api.depends(
        "invoice_ids.payment_state",
        "invoice_ids.state",
        "partner_id.customer_type",
    )
    def _compute_payment_completed(self):

        for order in self:

            order.payment_completed = True
            order.payment_warning = False

            if order.partner_id.customer_type != "direct":
                continue

            invoices = order.invoice_ids.filtered(
                lambda x:
                x.state == "posted"
                and x.move_type == "out_invoice"
            )

            if not invoices:
                order.payment_completed = False

                order.payment_warning = """
                <div class="alert alert-warning">
                    <strong>
                    Customer is Direct.
                    Invoice has not been created.
                    </strong>
                </div>
                """
                continue

            unpaid = invoices.filtered(
                lambda x: x.payment_state != "paid"
            )

            if unpaid:

                order.payment_completed = False

                order.payment_warning = """
                <div class="alert alert-danger">
                    <strong>
                    Delivery is blocked until invoice is fully paid.
                    </strong>
                </div>
                """
 
    payment_status = fields.Selection(
        [
            ("approved", "Approved"),
            ("waiting_payment", "Waiting Payment"),
            ("paid", "Paid"),
        ],
        string="Payment Status",
        compute="_compute_payment_status",
        store=True,
    )

    @api.depends(
        "partner_id.customer_type",
        "invoice_ids.payment_state",
        "invoice_ids.state",
    )
    def _compute_payment_status(self):

        for order in self:

            if order.partner_id.customer_type == "approved":
                order.payment_status = "approved"
                continue

            invoices = order.invoice_ids.filtered(
                lambda x: x.state == "posted"
                and x.move_type == "out_invoice"
            )

            if not invoices:
                order.payment_status = "waiting_payment"
                continue

            if all(inv.payment_state == "paid" for inv in invoices):
                order.payment_status = "paid"
            else:
                order.payment_status = "waiting_payment"