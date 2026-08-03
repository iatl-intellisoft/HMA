# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_total_deduction(self):
        """
        A method to compute total deduction amount
        """
        for rec in self:
            total_penalty = 0.00
            total_other = 0.00
            print("here")
            penalty_ids = rec.env['hr.deduction'].search([('employee_id', '=', rec.employee_id.id),
                                                                  ('state', '=', 'approve'),
                                                                  ('start_date','>=',rec.date_from),
                                                                  ('type_id','ilike', 'penalty'),
                                                                  ('end_date', '<=', rec.date_to),
                                                                  ])
            print("penalty_ids")
            print(penalty_ids)
            for line in penalty_ids:
                total_penalty += line.de_amount
            deduct_ids = rec.env['hr.deduction'].search([('employee_id', '=', rec.employee_id.id),
                                                           ('state', '=', 'approve'),
                                                           ('start_date', '>=', rec.date_from),
                                                           ('type_id', 'ilike', 'other deduct'),
                                                           ('end_date', '<=', rec.date_to),
                                                           ])
            for line in deduct_ids:
                total_other += line.de_amount
            rec.total_deduct_amount = total_penalty + total_other
            rec.total_penalty_deduct = total_penalty
            rec.total_other_deduct = total_other

    deduct_ids = fields.Many2many('hr.deduction', 'hr_deduction_payslip_rel', 'deduct_ids', 'payslip_id', string='Deductions')
    total_deduct_amount = fields.Float(string="Total Deduction Amount", compute='compute_total_deduction')
    total_penalty_deduct = fields.Float(string="Total Deduction Amount", compute='compute_total_deduction')
    total_other_deduct = fields.Float(string="Total Deduction Amount", compute='compute_total_deduction')

    def get_deduction(self):
        """
        A method to get deduction
        """
        for rec in self:
            rec.deduct_ids = self.env['hr.deduction'].search([('employee_id', '=', rec.employee_id.id),
                                                              ('state', '=', 'approve'),
                                                              '|',
                                                              '|',
                                                              '&',
                                                              ('start_date', '<=', rec.date_from),
                                                              ('end_date', '>',rec.date_from),
                                                             
                                                              '&',
                                                              ('start_date', '>=',rec.date_from),
                                                              ('end_date', '<=', rec.date_to),
                                                              
                                                              '&',
                                                              ('start_date','>=',rec.date_from),
                                                              ('end_date', '>=', rec.date_to),
                                                              ]).ids

    def compute_sheet(self):
        self.get_deduction()
        return super(HrPayslip, self.sudo()).compute_sheet()

    def action_payslip_cancel(self):
        """
        A method to cancel payslip deduction
        """
        res = super(HrPayslip, self).action_payslip_cancel()
        for rec in self:
            rec.deduct_ids.write({'payslip_id': False})
        return res

    def unlink(self):
        self.deduct_ids = False
        return super(HrPayslip, self).unlink()  
