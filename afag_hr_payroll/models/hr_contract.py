# -*- coding: utf-8 -*-

from odoo import models, fields, api,_


class Contract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Contract Extension'

    total_wage = fields.Monetary(compute='_compute_wage_total')
    payment_type = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], 'Payment Type', default='bank')
    no_gosi = fields.Boolean('No Gosi?')

    def _compute_wage_total(self):
        for rec in self:
            rec.total_wage = rec.wage + rec.l10n_sa_housing_allowance + rec.l10n_sa_transportation_allowance+ rec.l10n_sa_other_allowances

    def compute_settlement(self, payslip, code=None):
        result = 0.0
        settlement = self.env['hr.employee.settlement'].search(
            [('employee_id', '=', self.employee_id.id), ('state','=','done')]).filtered(lambda x:x.start_date <= payslip.date_from and payslip.date_to <= x.end_date)
        for rec in settlement:
            if rec.settlement_id.code == code:
                result = rec.amount
                if rec.sudo().settlement_id.type == "ded":
                    result *= -1
        return float(result)

    def compute_paid_leave(self, payslip, code=None):
        result = 0.0
        leaves = (self.env['hr.leave'].search(
            [('employee_id', '=', payslip.employee_id.id), ('state','=','validate')]).filtered(lambda
                                         x:x.request_date_from >= payslip.date_from
                                           and x.request_date_to <= payslip.date_to and x.holiday_status_id.work_entry_type_id.code==code and x.is_paid))
        for leave in leaves:
            result += leave.number_of_days
        return result

    def get_overlap_days(self, range1_start, range1_end, range2_start, range2_end):
        if range1_start <= range2_end and range1_end >= range2_start:
            overlap_start = max(range1_start, range2_start)
            overlap_end = min(range1_end, range2_end)
            return (overlap_end - overlap_start).days + 1
        return 0

    def _compute_unpaid_leaves(self, payslip_id, code=None):
        unpaid_days = 0
        unpaid_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', payslip_id.contract_id.employee_id.id), ('state', '=', 'validate'),
            ('holiday_status_id.work_entry_type_id.code', '=', code)])
        for record in unpaid_leaves:
            unpaid_days += payslip_id.contract_id.get_overlap_days(payslip_id.date_from, payslip_id.date_to,
                                                                   record.request_date_from,
                                                                   record.request_date_to)
        return unpaid_days
