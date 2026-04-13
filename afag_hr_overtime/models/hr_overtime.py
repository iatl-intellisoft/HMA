# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class HrOvertime(models.Model):
    _name = 'hr.overtime'
    _description = 'saudi hr overtime'
    _inherit = ['mail.thread','mail.activity.mixin', 'resource.mixin',]


    number = fields.Char(index=True, readonly=True)
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date")
    employee_id = fields.Many2one('hr.employee', 'Employee')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', string='Department')
    calendar_id = fields.Many2one('resource.calendar', related='employee_id.resource_calendar_id',
                                           string='Working Hours')
    analytic_account_id = fields.Many2one('account.analytic.account')
    notes = fields.Text('Description')
    state = fields.Selection([('draft', 'Draft'), ('hro', 'HR Officer'), ('done', 'Done'), ('cancel', 'Cancelled')],
                             default='draft')
    total_normal_hours = fields.Float('Normal Hours', compute='_compute_no_hours')
    total_weekend_hours = fields.Float('Weekend Hours')
    total_global_leave_hours = fields.Float('Holiday Hours')
    total_amount = fields.Float('Total Amount')
    line_ids = fields.One2many('hr.overtime.line', 'request_id', 'Details')

    _rec_name = 'number'

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        for vals in vals_list:
            vals['number'] = self.env['ir.sequence'].next_by_code(self._name)
        return super(HrOvertime, self).create(vals_list)

    @api.depends('line_ids')
    def _compute_no_hours(self):
        for rec in self:
            normal_hours = 0.0
            weekend_hours = 0.0
            global_leave_hours = 0.0
            total_amount = 0.0

            working_days = rec.resource_calendar_id.attendance_ids.mapped('dayofweek')
            global_leaves = rec.resource_calendar_id.global_leave_ids
            for line in rec.line_ids:
                is_global = False
                workday = line.date.weekday()
                if global_leaves:
                    for gl in global_leaves:
                        if gl.date_from.date() <= line.date <= gl.date_to.date():
                            global_leave_hours += line.no_hours
                            is_global = True
                if is_global:
                    continue

                if str(line.date.weekday()) in working_days:
                    normal_hours += line.no_hours
                else:
                    weekend_hours += line.no_hours
            rec.total_normal_hours = normal_hours
            rec.total_weekend_hours = weekend_hours
            rec.total_global_leave_hours = global_leave_hours
            overtime_config = self.env['hr.overtime.config'].search([], limit=1)
            overtime_equation = overtime_config.overtime_equation
            local_dict = {"wage": rec.sudo().employee_id.contract_id.wage, 'total_normal_hours': normal_hours,
                          'total_weekend_hours': weekend_hours, 'total_global_leave_hours': global_leave_hours}
            result = eval(overtime_equation, local_dict)
            rec.total_amount = result

    def unlink(self):
        if any(self.filtered(lambda overtime: overtime.state not in ('draft', 'cancel'))):
            raise UserError(_('You cannot delete a request which is not draft or cancelled!'))
        return super(HrOvertime, self).unlink()

    def action_submit(self):
        for rec in self:
            rec.state = 'hro'

    def action_confirm(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'


class HrOvertimeLine(models.Model):
    _name = 'hr.overtime.line'
    _description = 'saudi hr overtime lines'

    date = fields.Date('Date')
    no_hours = fields.Float('No of Hours')
    request_id = fields.Many2one('hr.overtime')


class Contract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Contract Extension'

    def compute_overtime(self, payslip):
        amount = 0.0
        for rec in self.env['hr.overtime'].search(
                [('state', '=', 'done'), ('employee_id', '=', payslip.contract_id.employee_id.id), ('date', '>=', payslip.date_from), ('date', '<=', payslip.date_to)]):
            amount += rec.total_amount
        return amount
