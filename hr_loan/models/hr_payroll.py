# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrPayslip(models.Model):
    """"""
    _inherit = 'hr.payslip'

    def compute_total_paid_loan(self):
        """
        A method to compute total paid loan amount
        """
        total = 0.00
        for line in self.loan_ids:
            total += line.paid_amount
        self.total_amount_paid = total

    loan_ids = fields.One2many('hr.loan.line', 'payslip_id', string="Loans", readonly=True)
    total_amount_paid = fields.Float(string="Total Loan Amount", compute='compute_total_paid_loan')

    def get_loan(self):
        """
        A method to get posted and approved employee's loan
        """
        print
        
        domain = []
        for rec in self:
            # array = []
            rec.loan_ids.write({'payslip_id': False})
            loan_ids = self.env['hr.loan.line'].search([('employee_id', '=', rec.employee_id.id),
                                                        ('paid', '=', False), ('paid_date', '>=', rec.date_from),
                                                        ('paid_date', '<=', rec.date_to),
                                                        ('loan_id.move_id.state', '=', 'posted'),
                                                        ('loan_id.state','=','approve')
                                                        ])
            # for loan in loan_ids:
            #     if loan.loan_id.state == 'approve':
            #         array.append(loan.id)
            # rec.loan_ids = loan_ids.ids if loan_ids or []
            loan_ids.write({'payslip_id': rec.id})
        return True

    def compute_sheet(self):
        """
        inherit from compute_sheet to compute loan from payslip
        """
        self.get_loan()
        return super(HrPayslip, self).compute_sheet()

    # def action_payslip_done(self):
    #     """
    #     A method to loan from payslip
    #     """
    #     res = super(HrPayslip, self).action_payslip_done()
    #     for rec in self:
    #         loan_lines = self.env['hr.loan.line'].search([('payslip_id', '=', rec.id)])
    #         #if loan_lines:
    #         for line in rec.loan_ids:
    #             line.action_paid_amount()
    #     return res

    def action_update_related_records(self):
        """
        Function to be updated by process that calculated using payroll
        """
        res = super(HrPayslip, self).action_update_related_records()
        for rec in self:
            rec.loan_ids.action_paid_amount()
        return res

    def action_payslip_cancel(self):
        """
        action_payslip_cancel method Inherited and update payslip and state to set loan in cancel state.
        """
        res = super(HrPayslip, self).action_payslip_cancel()
        for rec in self:
            if rec.loan_ids:
                rec.loan_ids.write({'payslip_id': False,'paid': False})
        return res
