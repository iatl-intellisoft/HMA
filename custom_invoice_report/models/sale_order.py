# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_print_tax_base_invoice(self):
        """
        Print invoice report replacing unit price with product's tax_base_amount.
        """
        self.ensure_one()

        # Validate that all order lines have a product with tax_base_amount
        lines_without_value = self.order_line.filtered(
            lambda l: l.product_id and not l.product_id.tax_base_amount
        )
        if lines_without_value:
            product_names = ', '.join(lines_without_value.mapped('product_id.name'))
            raise UserError(
                _('The following products have no Tax Base Amount set:\n%s') % product_names
            )

        return self.env.ref(
            'custom_invoice_report.action_report_tax_base_invoice'
        ).report_action(self)
