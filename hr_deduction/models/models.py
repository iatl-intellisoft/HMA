# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class HrDeduction(models.Model):
    _name = 'hr.deduction'
    _inherit = ['mail.thread']
    _description = "HR Deduction"

    @api.depends('deducted_by', 'employee_id', 'type_id', 'hours_ded', 'amount')
    def _compute_de_amount(self):
        """
        A method to compute deduction amount
        """
        for record in self:
            de_amount = 0.00
            if record.deducted_by == 'hours':
                if record.type_id.rule_id:
                    de_amount = record.hours_ded * record.type_id.rule_id.compute_rule_amount(record.employee_id)
            if record.deducted_by == 'amount':
                de_amount = record.amount
            record.de_amount = de_amount

    name = fields.Char(string="Ref:", default="/")
    date = fields.Date(string="Date Request", default=fields.Date.today(), required=True)
    approve_date = fields.Date(string="Approve Date")
    employee_id = fields.Many2one('hr.employee',
                                  string="Employee", required=True, )
    parent_id = fields.Many2one('hr.employee', related="employee_id.parent_id", string="Manager")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id",
                                    string="Department")
    job_id = fields.Many2one('hr.job', related="employee_id.job_id", string="Job Position")
    deducted_by = fields.Selection(string='Deduct By', related="type_id.deducted_by",
                                   selection=[('amount', 'Amount'), ('hours', 'Hours')], store=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env.company)
    type_id = fields.Many2one('hr.deduct.conf', string="Type", required=True, ondelete='restrict')
    hours_ded = fields.Float(string='Deduct Hours', help='Number of houres')
    amount = fields.Float(string=" Amount")
    de_amount = fields.Float(string="Deduct Amount", compute='_compute_de_amount')
    payslip_id = fields.Many2many('hr.payslip', 'hr_deduction_payslip_rel', 'payslip_id', 'deduct_ids', string='Payslips')
    description = fields.Html(string='Description')
    batch_id = fields.Many2one('hr.deduction.batch', string='batch', ondelete='set null', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'confirm'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Cancel'),
    ], string="State", default='draft', tracking=5, copy=False, )
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    def unlink(self):
        """
        A method to delete deduction
        """
        for deduction in self:
            if deduction.state not in ('draft',):
                raise UserError(_('You can not delete record not in draft state.'))
        return super(HrDeduction, self).unlink()

    @api.model
    def create(self, values):
        """
        A method to create deduction sequence
        """
        values['name'] = self.env['ir.sequence'].get('hr.deduction.req') or ' '
        res = super(HrDeduction, self).create(values)
        return res

    def action_refuse(self):
        """
        A method to refuse deduction
        """
        return self.write({'state': 'refuse'})

    def action_set_to_draft(self):
        """
        A method to make deduction as draft
        """
        return self.write({'state': 'draft'})

    def action_approve(self):
        """
        A method to approve deduction
        """
        approve_date = fields.Date.today()
        self.write({'state': 'approve', 'approve_date': approve_date})

    def action_confirm(self):
        """
        A method to confirm deduction
        """
        if self.description == "<p><br></p>":
            raise UserError(_("Please add Reason before you approve"))
        self.write({'state': 'confirm'})

    def action_cancel(self):
        """
        A method to cancel deduction
        """
        if self.payslip_id:
            raise ValidationError(_("Sorry! you can't cancel this record; There is a payslip /s for this record!"))

        self.state = 'cancel'

