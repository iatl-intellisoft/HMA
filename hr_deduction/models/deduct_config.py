# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import fields, models

class HrDeductConf(models.Model):
    """"""
    _name = 'hr.deduct.conf'

    name = fields.Char(string="Name", required=True)
    rule_id = fields.Many2one('hr.salary.rule', string='Compute ')
    deducted_by = fields.Selection(string='Deduct By', required=True,
                                   selection=[('amount', 'Amount'), ('hours', 'Hours')], default='amount')
    code = fields.Char(string='Code')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

class ResConfigSettings(models.TransientModel):
    """"""
    _inherit = 'res.config.settings'

    deduction_template_id = fields.Many2one('mail.template', string='Deduction Template', default=lambda self: self.env[
        'res.company']._company_default_get().deduction_template_id, related='company_id.deduction_template_id',
                                            readonly=False)
                                            
class ResCompany(models.Model):
    """"""
    _inherit = 'res.company'

    deduction_template_id = fields.Many2one('mail.template', string='Deduction Template',
                                            domain="[('model','=','hr.deduction.batch')]")
