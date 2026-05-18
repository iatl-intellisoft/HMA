from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer = fields.Boolean("Is Customer")
    vendor = fields.Boolean("Is Vendor")
    code = fields.Char(string="Customer Code")

    # _sql_constraints = [('phone_unique', 'unique(phone)', 'Phone Number Must Be unique!')]

    @api.constrains('phone')
    def _check_phone_no(self):
        phone_count = self.env['res.partner'].search_count([('phone', '=', self.phone)])
        # phone_no = len(self.phone)
        if phone_count > 1:
            raise ValidationError(_('Phone Number should be unique in company'))
        # elif phone_no != 10:
        #     raise ValidationError(_('Phone Number should be 10 number!'))
        #

    @api.onchange('vendor')
    def fill_is_vendor(self):
        if self.vendor:
            self.supplier_rank += 1
        else:
            self.supplier_rank = 0

    @api.onchange('customer')
    def fill_is_customer(self):
        if self.customer:
            self.customer_rank += 1
        else:
            self.customer_rank = 0


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_company(self):
        ''' Get the default company. '''
        journal = self._get_default_journal()
        return journal.company_id or self.env.company

    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 store=True, readonly=True,
                                 # default=_get_default_company,
                                 compute='_compute_company_id')
