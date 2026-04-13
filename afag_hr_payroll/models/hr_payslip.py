from odoo import models, api, Command, fields


class HrPayslip(models.Model):
    """ Extends the 'hr.payslip' model to include
    additional functionality related to employee loans."""
    _inherit = 'hr.payslip'
    
    payment_type = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], related='contract_id.payment_type', store=True)
    employer_id = fields.Many2one('res.partner', related='contract_id.employee_id.employer_id', store=True)

    worked_days = fields.Float(string="Worked Days", compute="_compute_worked_days")

    @api.depends('line_ids', 'employee_id', 'contract_id')
    def _compute_worked_days(self):
        for payslip in self:
            worked_days = 0.0
            # You can filter for work entry type or other conditions here
            for line in payslip.worked_days_line_ids:
                if line.code == 'WORK100':  # Example work entry code
                    worked_days += line.number_of_days  # Or other field that represents worked days
            payslip.worked_days = worked_days
