from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_split_payment = fields.Boolean(
    compute="_compute_is_split_payment"
    )
    customer_cash_payment = fields.Boolean(compute="_compute_split_flags")
    customer_bank_payment = fields.Boolean(compute="_compute_split_flags")
    vendor_cash_payment   = fields.Boolean(compute="_compute_split_flags")
    vendor_bank_payment   = fields.Boolean(compute="_compute_split_flags")

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
    def _compute_split_flags(self):
        ctx = self.env.context
        ccp = bool(ctx.get("customer_cash_payment"))
        cbp = bool(ctx.get("customer_bank_payment"))
        vcp = bool(ctx.get("vendor_cash_payment"))
        vbp = bool(ctx.get("vendor_bank_payment"))
        if ccp or vcp:
            jtype = "cash"
        elif cbp or vbp:
            jtype = "bank"
        else:
            jtype = False
        for rec in self:
            rec.customer_cash_payment = ccp
            rec.customer_bank_payment = cbp
            rec.vendor_cash_payment   = vcp
            rec.vendor_bank_payment   = vbp
            rec.split_journal_type    = jtype

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
