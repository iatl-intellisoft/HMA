# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.translate import html_translate

class HrDeductionaBatch(models.Model):
    """"""
    _name = 'hr.deduction.batch'
    _inherit = ['mail.thread']
    _description = "HR Deduction Batch"

    description = fields.Html(string='Description')
    name = fields.Char(string='name', default="/")
    date = fields.Date(string='Date', default=fields.Date.context_today, )
    approve_date = fields.Date(string='Approved Date', )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'confirm'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Cancel'),
    ], string="State", default='draft', tracking=5, copy=False, )

    batch_type = fields.Selection([
        ('all_staff', 'All Staff'),
        ('employee', 'Employee'),
        ('selected_employee', 'Selected Employees'),

    ], string="Batch Type", default='all_staff', tracking=5, copy=False, )

    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='set null', )
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_deduction_batch_rel', 'employee_id', 'batch_id',
                                    string='Employees')
    type_id = fields.Many2one('hr.deduct.conf', string="Type", required=True, ondelete='restrict')
    dedcution_ids = fields.One2many('hr.deduction', 'batch_id', string=u'dedcution', )
    hours_ded = fields.Float(string='Deduct Hours', help='Number of houres')
    amount = fields.Float(string=" Amount")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env.company)
    deducted_by = fields.Selection(string='Deduct By', related="type_id.deducted_by",
                                   selection=[('amount', 'Amount'), ('hours', 'Hours')])
    deduction_website_description = fields.Html('Body Template', sanitize_attributes=False, translate=html_translate,
                                                compute="get_deduction_website_description")
    deduction_template_id = fields.Many2one('mail.template', string='Deduction Template',
                                            related='company_id.deduction_template_id', readonly=False, )
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    @api.depends('deduction_template_id', 'deduction_template_id.body_html', 'dedcution_ids')
    def get_deduction_website_description(self):
        """
        A method to create deduction website description template
        """
        for rec in self:
            rec.deduction_website_description += rec.deduction_website_description
            if rec.deduction_template_id and rec.id:
                fields = ['body_html']
                template_values = rec.deduction_template_id.generate_email([rec.id], fields=fields)
                rec.deduction_website_description = template_values[rec.id].get('body_html')

    def get_deduction_template(self, res, dedction_template):
        """
        A method to create template
        """
        if dedction_template:
            fields = ['body_html']
            returned_fields = fields
            values = dict.fromkeys([res.id], False)
            template_values = res.env['mail.template'].browse(dedction_template).generate_email([res.id], fields=fields)
            for res_id in [res.id]:
                res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if
                                     template_values[res_id].get(field))
                res.deduction_website_description = res_id_values.pop('body_html', '')
                values[res_id] = res_id_values

    @api.model
    def create(self, values):
        """
        A method to create deduction batch sequence
        """
        values['name'] = self.env['ir.sequence'].get('hr.deduction.batch.req') or 'NEW'
        res = super(HrDeductionaBatch, self).create(values)

        return res

    def compute_deduction(self):
        """
        A method to compute deduction
        """
        line_obj = self.env['hr.deduction'].search([])
        if self.batch_type == 'all_staff':
            employees = self.env['hr.employee'].search([('active', '=', True)])
        elif self.batch_type == 'employee':
            employees = self.employee_id
        elif self.batch_type == 'selected_employee':
            employees = self.employee_ids
        if self.dedcution_ids:
            for line in self.dedcution_ids:
                if line.employee_id not in employees:
                    line.unlink()
        res = [r['employee_id'][0] for r in self.dedcution_ids.read(['employee_id'])]
        for rec in employees:
            if rec.id not in res:
                line_obj.create({
                    'date': self.date,
                    'employee_id': rec.id,
                    'batch_id': self.id,
                    'type_id': self.type_id.id,
                    'amount': self.amount,
                    'hours_ded': self.hours_ded,
                    'company_id': self.company_id.id,
                    'start_date': self.start_date,
                    'end_date': self.end_date,

                })

    def unlink(self):
        """
        A method to delete deduction
        """
        for deduction in self:
            if deduction.state not in ('draft',):
                raise UserError(_('You can not delete record not in draft state.'))
        return super(HrDeductionaBatch, self).unlink()

    def action_approve(self):
        """
        A method to approve deduction
        """
        approve_date = fields.Date.today()
        self.write({'state': 'approve', 'approve_date': approve_date})
        for rec in self.dedcution_ids:
            rec.action_approve()

    def action_confirm(self):
        """
        A method to confirm deduction
        """
        self.write({'state': 'confirm'})
        for rec in self.dedcution_ids:
            rec.action_confirm()

    def action_refuse(self):
        """
        A method to refuse deduction
        """
        self.write({'state': 'refuse'})
        for rec in self.dedcution_ids:
            rec.action_refuse()

    def action_cancel(self):
        """
        A method to cancel deduction
        """
        self.write({'state': 'cancel'})
        for rec in self.dedcution_ids:
            rec.action_cancel()

    def action_set_to_draft(self):
        """
        A method to set deduction draft
        """
        self.write({'state': 'draft'})

