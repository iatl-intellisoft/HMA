from odoo import models, fields


class HrJob(models.Model):
    _inherit = 'hr.job'
 
    proposed_salary = fields.Float(string="Proposed Salary") 
    start_date = fields.Date(string="Start Date")
    probation_period = fields.Selection([
        ('3', '3 Months'),
        ('6', '6 Months'),
        ('other', 'Other'),
    ], string="Probation Period") 
