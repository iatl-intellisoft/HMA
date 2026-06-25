from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_split_payment = fields.Boolean(
    compute="_compute_is_split_payment"
    )

    def _compute_is_split_payment(self):
        flag = any([
            self.env.context.get('customer_cash_payment'),
            self.env.context.get('customer_bank_payment'),
            self.env.context.get('vendor_cash_payment'),
            self.env.context.get('vendor_bank_payment'),
        ])
        for rec in self:
            rec.is_split_payment = flag

    payment_mode = fields.Selection([
        ('customer_cash', 'Customer Cash'),
        ('customer_bank', 'Customer Bank'),
        ('vendor_cash', 'Vendor Cash'),
        ('vendor_bank', 'Vendor Bank'),
    ])

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        mode = self.env.context.get('payment_mode')

        if mode == 'customer_cash':
            res.update({
                'payment_type': 'inbound',
                'partner_type': 'customer',
            })
            self.is_split_payment = True

        elif mode == 'customer_bank':
            res.update({
                'payment_type': 'inbound',
                'partner_type': 'customer',
            })
            self.is_split_payment = True


        elif mode == 'vendor_cash':
            res.update({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
            })
            self.is_split_payment = True


        elif mode == 'vendor_bank':
            res.update({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
            })
            self.is_split_payment = True


        return res
