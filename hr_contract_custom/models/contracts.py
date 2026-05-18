from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
import time
from odoo.exceptions import UserError, AccessError, ValidationError
from dateutil.relativedelta import relativedelta


class Contracts(models.Model):
    _inherit = 'hr.contract'

    _sql_constraints = [
        ('state_unique', 'unique(employee_id, date, state)',
         _('Date + End Date Cannot be repeated in one employee!'))]


    #### adding offer state 
    state = fields.Selection([
        ('draft', 'New'),
        ('offer', 'Offer'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states',
        track_visibility='onchange', help='Status of the contract', default='draft', store='True')
    

    ##### this field will be replaced 
    #### struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', track_visibility='onchange')
    #### with a domain that "structes" are  in "structure_type_id.struct_ids" 
    #### and with default value =  "sturcture_tupe_id.default_struct_id"  
    # struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', track_visibility='onchange')


    ####### add tract_visibility='onchange' to the following fiedls
    name = fields.Char('Contract Reference', required=True, track_visibility='onchange')
    active = fields.Boolean(default=True, track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True,  track_visibility='onchange'
       , domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    department_id = fields.Many2one('hr.department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", track_visibility='onchange' , string="Department")


    job_id = fields.Many2one('hr.job', string='Job Position', track_visibility='onchange')
    date_start = fields.Date('Start Date', required=True, default=fields.Date.today,
                             help="Start date of the contract.", track_visibility='onchange')
    date_end = fields.Date('End Date', track_visibility='onchange',
                           help="End date of the contract (if it's a fixed-term contract).")
    trial_date_end = fields.Date('End of Trial Period', track_visibility='onchange',
                                 help="End date of the trial period (if there is one).")

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Schedule', track_visibility='onchange',
        default=lambda self: self.env['res.company']._company_default_get().resource_calendar_id.id)


    #### this field was replaced  
    # type_id = fields.Many2one('hr.contract.type', string="Employee Category", required=True,
    #                           track_visibility='onchange',
    #                           default=lambda self: self.env['hr.contract.type'].search([], limit=1))



    hour_wage = fields.Float(string='Hour wage', compute='_compute_hour_wage', store=True)
    age = fields.Integer(string="Age", related="employee_id.age",store=True)
    joining_date = fields.Date(string="Actual Joining Date", track_visibility='onchange')
    service_years = fields.Float(string='Service Years', compute='get_service_years', store=True)

    
    @api.depends('date_start','date_end')
    def get_service_years(self):
     
        for rec in self:
            if rec.date_end:
                rec.service_years=(rec.date_end-rec.date_start).days/365.2
            else:
                rec.service_years = (fields.date.today() - rec.date_start).days/365.2

    
    @api.constrains('state', 'employee')
    def check_state(self):
        for contract in self :
            contracts = contract.employee_id.contract_ids.filtered(lambda r: r.state == 'open')
            if len(contracts) > 1:
                raise UserError("Employee Cannot Have Two Running Contract!")

    @api.depends('wage', 'resource_calendar_id')
    def _compute_hour_wage(self):
        for record in self:
            if record.resource_calendar_id.hours_per_day != 0:
                averg = record.resource_calendar_id.hours_per_day * 30
                hour_wage = record.wage / averg
                record.hour_wage = hour_wage
            else:
                record.hour_wage = 0.0   

    

    

    ######## moved to hr_payrol_custom
    # def _create_mail_activity(self):
    #     # hr_user_group = self.env.ref('hr.group_hr_user')
    #     hr_user_group = self.company_id.hr_group_id

    #     users_of_hr_group = self.env['res.users'].search([('groups_id', '=', hr_user_group.id)]).ids
    #     contract_model = self.env['ir.model'].search([('model', '=', 'hr.contract')], limit=1).id,
    #     created_activitys = self.env['mail.activity'].search(
    #         [('res_model_id', '=', contract_model), ('create_throw_system', '=', True), ('res_id', '=', self.id)])
    #     if created_activitys:
    #         for activity in created_activitys:
    #             activity.unlink()
    #     summary = 'End of Trial Period' if self.state == 'offer' else 'End of Contract Period'
    #     offer_date_deadline = self.trial_date_end - relativedelta(days=self.type_id.alert_date) if self.trial_date_end else False
    #     contract_date_deadline = self.date_end - relativedelta(days=self.type_id.alert_date) if self.date_end else False
    #     date_deadline = offer_date_deadline if self.state == 'offer' else contract_date_deadline
    #     if date_deadline:
    #         for user in users_of_hr_group:
    #             activity = self.env['mail.activity'].create({
    #                 'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
    #                 'summary': summary,
    #                 'date_deadline': date_deadline,
    #                 'user_id': user,
    #                 'create_throw_system': True,
    #                 'res_id': self.id,
    #                 'res_model_id': self.env['ir.model'].search([('model', '=', 'hr.contract')], limit=1).id,
    #             })
    #     return True

    
    def action_draft(self):
        self.write({'state': 'draft'})

    
    def action_offer(self):
        self.write({'state': 'offer'})
        # return self._create_mail_activity()

    
    def action_open(self):
        if not self.joining_date:
            raise UserError(_('Please Enter actual employee join date.'))
        self.write({'state': 'open'})
        # return self._create_mail_activity()

    # def action_pending(self):
    #     self.write({'state': 'pending'})


    def action_cancel(self):
        self.write({'state': 'cancel'})

 
    def action_close(self):
        self.write({'state': 'close'})

    ###### moved to hr_payroll_custom
    # @api.onchange('date_start')
    # def _onchange_start_date(self):
    #     """ When changing the start date, also set end trail period to be after it by 3 monthes. """
    #     # self.trial_date_end = self.date_start + relativedelta(months=3)
    #     self.trial_date_end = self.date_start + relativedelta(months=self.type_id.trail_period)

   
    def unlink(self):
        for order in self:
            if order.state not in ('draft',):
                raise UserError(_('You can not delete record not in draft state.'))
        return super(Contracts, self).unlink()



#### this model was replaced by 'hr.payroll.structure.type' , so the new fields will be added to
#### the new model in hr_payroll_custom module 
# class ContractTypes(models.Model):
#     _inherit = 'hr.contract.type'

#     alert_date = fields.Integer(string="Notify Days before contract End", track_visibility='onchange', default='15',
#                                 help="number of days to send notification before end of contract.")
#     trail_period = fields.Integer(string="Trail Period ( month ) ", track_visibility='onchange', default='3',
#                                   help="Trail Period in Months")




