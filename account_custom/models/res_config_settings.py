from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    module_financial_year_end_process = fields.Boolean("Close Financial Year Process")
    group_fiscal_year = fields.Boolean(string='Fiscal Years', implied_group='account_accountant.group_fiscal_year' , related="company_id.group_fiscal_year", readonly=False)

class Company(models.Model):
    _inherit = 'res.company'
    
    group_fiscal_year = fields.Boolean(string='Fiscal Years')

