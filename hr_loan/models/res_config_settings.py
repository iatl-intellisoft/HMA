from odoo import fields, models


class ConfigSettings(models.TransientModel):
    """"""
    _inherit = 'res.config.settings'

    loan_request_template_id = fields.Many2one('mail.template', string='Loan Request Template',
                                               related='company_id.loan_request_template_id', readonly=False)
    salary_advance_template_id = fields.Many2one('mail.template', string='Salary Advance Template',
                                                 related='company_id.salary_advance_template_id', readonly=False)


class ResCompany(models.Model):
    """"""
    _inherit = 'res.company'

    loan_request_template_id = fields.Many2one('mail.template', string='Loan Request Template',
                                               domain="[('model','=','hr.loan')]")
    salary_advance_template_id = fields.Many2one('mail.template', string='Salary Advance Template',
                                                 domain="[('model','=','hr.loan')]")
