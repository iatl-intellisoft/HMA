# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        invalid = self.filtered(lambda p: p.amount <= 0)
        if invalid:
            new_label = _('(new)')
            names = ', '.join(p.name or new_label for p in invalid)
            raise UserError(_(
                "Cannot confirm payment(s) %s: amount must be greater than zero.",
                names,
            ))
        return super().action_post()
