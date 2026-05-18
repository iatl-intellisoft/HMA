from datetime import date, datetime, time, timedelta
from collections import defaultdict
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo import tools, _


class HrContract(models.Model):
    """"""
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type", required=True,
                                        track_visibility='onchange', )
    struct_id = fields.Many2one('hr.payroll.structure', readonly=False, string='Salary Structure',
                                track_visibility='onchange',required=True)

    @api.onchange('structure_type_id')
    def onchange_structure_type(self):
        """
        A method to change structure type
        """
        for record in self:
            if record.structure_type_id:
                return {'domain': {'struct_id': [('id', 'in', record.structure_type_id.struct_ids.ids)]}}

    def _create_mail_activity(self):
        """"""
        # hr_user_group = self.env.ref('hr.group_hr_user')
        hr_user_group = self.company_id.hr_group_id
        users_of_hr_group = self.env['res.users'].search([('groups_id', '=', hr_user_group.id)]).ids
        contract_model = self.env['ir.model'].search([('model', '=', 'hr.contract')], limit=1).id,
        created_activitys = self.env['mail.activity'].search(
            [('res_model_id', '=', contract_model), ('create_throw_system', '=', True), ('res_id', '=', self.id)])
        if created_activitys:
            for activity in created_activitys:
                activity.unlink()
        summary = 'End of Trial Period' if self.state == 'offer' else 'End of Contract Period'
        offer_date_deadline = self.trial_date_end - relativedelta(
            days=self.structure_type_id.alert_date) if self.trial_date_end else False
        contract_date_deadline = self.date_end - relativedelta(
            days=self.structure_type_id.alert_date) if self.date_end else False
        date_deadline = offer_date_deadline if self.state == 'offer' else contract_date_deadline
        if date_deadline:
            for user in users_of_hr_group:
                activity = self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': summary,
                    'date_deadline': date_deadline,
                    'user_id': user,
                    'create_throw_system': True,
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model'].search([('model', '=', 'hr.contract')], limit=1).id,
                })
        return True

    def action_offer(self):
        """"""
        self.write({'state': 'offer'})
        return self._create_mail_activity()

    def action_open(self):
        """"""
        if not self.joining_date:
            raise UserError(_('Please Enter actual employee join date.'))
        self.write({'state': 'open'})
        return self._create_mail_activity()

    @api.onchange('date_start')
    def _onchange_start_date(self):
        """ When changing the start date, also set end trail period to be after it by 3 monthes. """
        # self.trial_date_end = self.date_start + relativedelta(months=3)
        self.trial_date_end = self.date_start + relativedelta(months=self.structure_type_id.trail_period)


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    alert_date = fields.Integer(string="Notify Days before contract End", track_visibility='onchange', default='15',
                                help="number of days to send notification before end of contract.")
    trail_period = fields.Integer(string="Trail Period ( month ) ", track_visibility='onchange', default='3',
                                  help="Trail Period in Months")

class HrEmployee(models.Model):
    """"""
    _inherit = 'hr.employee'

    bank_id = fields.Many2one('res.bank', related='bank_account_id.bank_id', readonly=False,store=True) 
