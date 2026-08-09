# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.osv.expression import AND



class ShAccountJournalRestrict(models.Model):
    _inherit = 'account.journal'

    @api.model
    def default_get(self, fields):
        rec = super(ShAccountJournalRestrict, self).default_get(fields)

        users = self.env.company.sh_user_ids.ids
        rec.update({
            'user_ids': [(6, 0, users)]
        })
        return rec

    user_ids = fields.Many2many(
        'res.users', string="Users", copy=False)

    # To apply domain to action_________ 2
    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):

        if (
            self.env.user.has_group("sh_journal_restrict.group_journal_restrict_feature") and not
            (self.env.user.has_group("base.group_erp_manager"))
        ):
            sh_domain = [
                ("user_ids", "in", self.env.user.id), ('name', 'ilike', name)
            ]
        else:
            sh_domain = [('name', 'ilike', name)]
        return super()._name_search(name, expression.AND([sh_domain,domain]), operator, limit, order)

    # To apply domain to load menu_________ 1
    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        _ = self._context or {}
        if (
            self.env.user.has_group("sh_journal_restrict.group_journal_restrict_feature") and not
            (self.env.user.has_group("base.group_erp_manager"))
        ):
            domain += [
                ("user_ids", "in", self.env.user.id),
            ]
        return super(ShAccountJournalRestrict, self).search_fetch(
            domain, field_names, offset, limit, order)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _search(self, domain, *args, **kwargs):

        if (
            not self.env.su and
            self.env.user.has_group("sh_journal_restrict.group_hide_restricted_journal") and
            not self.env.user.has_group("base.group_erp_manager")
        ):
            restrict_domain = [('journal_id.user_ids', 'in', [self.env.user.id])]

            domain = expression.AND([domain, restrict_domain])

        return super()._search(domain, *args, **kwargs)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _search(self, domain, *args, **kwargs):

        if (
            not self.env.su and
            self.env.user.has_group("sh_journal_restrict.group_hide_restricted_journal") and
            not self.env.user.has_group("base.group_erp_manager")
        ):
            restrict_domain = [
                ('journal_id.user_ids', 'in', [self.env.user.id]),

            ]
            domain = expression.AND([domain, restrict_domain])


        return super()._search(domain, *args, **kwargs)
