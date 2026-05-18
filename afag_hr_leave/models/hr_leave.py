from odoo import api, fields, models, tools, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime, time
from odoo.addons.resource.models.utils import HOURS_PER_DAY
from math import ceil
from collections import defaultdict
import pytz
from pytz import timezone, UTC
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT




class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    is_lost = fields.Boolean(string="Lost Request")
    is_purchased = fields.Boolean()
    is_paid = fields.Boolean(string="Paid")
    move_id = fields.Many2one('account.move')

    @api.constrains('state', 'holiday_status_id')
    def _check_gender(self):
        for record in self:
            if record.state not in ['draft', 'cancel', 'refuse'] and record.holiday_status_id.gender:
                if record.employee_id.gender != record.holiday_status_id.gender:
                    raise ValidationError(_('This Leave is not allowed for this gender.'))

    @api.constrains('state', 'holiday_status_id')
    def _check_marital_status(self):
        for record in self:
            if record.state not in ['draft', 'cancel', 'refuse'] and record.holiday_status_id.marital:
                if record.employee_id.marital != record.holiday_status_id.marital:
                    raise ValidationError(_('This Leave is not allowed for this marital status.'))

    # @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit')
    # def _compute_duration(self):
    #     for holiday in self:
    #         days, hours = holiday._get_duration()
    #         if (holiday.holiday_status_id.calc_type == 'calendar' or
    #                 (holiday.holiday_status_id.calc_type == 'employee_grade' and holiday.employee_id.annual_leave_type=='calendar')):
    #             public_holidays = holiday.employee_id._get_public_holidays(holiday.request_date_from, holiday.request_date_to)
    #             days = (holiday.date_to - holiday.date_from).days -len(public_holidays)+ 1
    #             hours = HOURS_PER_DAY * days
    #         holiday.number_of_hours = hours
    #         holiday.number_of_days = days


    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        """
        This method is factored out into a separate method from
        _compute_duration so it can be hooked and called without necessarily
        modifying the fields and triggering more computes of fields that
        depend on number_of_hours or number_of_days.
        """
        result = {}
        employee_leaves = self.filtered('employee_id')
        employees_by_dates_calendar = defaultdict(lambda: self.env['hr.employee'])
        for leave in employee_leaves:
            if not leave.date_from or not leave.date_to:
                continue
            employees_by_dates_calendar[(leave.date_from, leave.date_to, leave.holiday_status_id.include_public_holidays_in_duration, resource_calendar or leave.resource_calendar_id)] += leave.employee_id
        # We force the company in the domain as we are more than likely in a compute_sudo
        domain = [('time_type', '=', 'leave'),
                  ('company_id', 'in', self.env.companies.ids + self.env.context.get('allowed_company_ids', [])),
                  '|', ('holiday_id', '=', False), ('holiday_id', 'not in', employee_leaves.ids)]
        # Precompute values in batch for performance purposes
        work_time_per_day_mapped = {
            (date_from, date_to, calendar): employees.with_context(
                    compute_leaves=not include_public_holidays_in_duration)._list_work_time_per_day(date_from, date_to, domain=domain, calendar=calendar)
            for (date_from, date_to, include_public_holidays_in_duration, calendar), employees in employees_by_dates_calendar.items()
        }
        work_days_data_mapped = {
            (date_from, date_to, calendar): employees._get_work_days_data_batch(date_from, date_to, compute_leaves=not include_public_holidays_in_duration, domain=domain, calendar=calendar)
            for (date_from, date_to, include_public_holidays_in_duration, calendar), employees in employees_by_dates_calendar.items()
        }
        for leave in self:
            calendar = resource_calendar or leave.resource_calendar_id
            if not leave.date_from or not leave.date_to or not calendar:
                result[leave.id] = (0, 0)
                continue
            hours, days = (0, 0)
            if leave.employee_id:
                if leave.holiday_status_id.calc_type == 'calendar' or leave.employee_id.annual_leave_type == 'calendar':
                    # Get public holidays
                    public_holidays = leave.sudo().employee_id._get_public_holidays(leave.date_from.date(), leave.date_to.date())
                    # Compute calendar days
                    days = (leave.date_to.date() - leave.date_from.date()).days + 1
                    if not leave.holiday_status_id.include_public_holidays_in_duration:
                        # Exclude public holidays
                        days -= len(public_holidays)
                    hours = days * HOURS_PER_DAY  # Assuming standard hours per day
                elif leave.leave_type_request_unit == 'day' and check_leave_type:
                    # list of tuples (day, hours)
                    work_time_per_day_list = work_time_per_day_mapped[(leave.date_from, leave.date_to, calendar)][leave.employee_id.id]
                    days = len(work_time_per_day_list)
                    hours = sum(map(lambda t: t[1], work_time_per_day_list))
                else:
                    work_days_data = work_days_data_mapped[(leave.date_from, leave.date_to, calendar)][leave.employee_id.id]
                    hours, days = work_days_data['hours'], work_days_data['days']
            else:
                today_hours = calendar.get_work_hours_count(
                    datetime.combine(leave.date_from.date(), time.min),
                    datetime.combine(leave.date_from.date(), time.max),
                    False)
                hours = calendar.get_work_hours_count(leave.date_from, leave.date_to, compute_leaves=not leave.holiday_status_id.include_public_holidays_in_duration)
                days = hours / (today_hours or HOURS_PER_DAY)
            if leave.leave_type_request_unit == 'day' and check_leave_type:
                days = ceil(days)
            result[leave.id] = (days, hours)
        return result


    @api.onchange('date_from', 'date_to', 'holiday_status_id', 'holiday_status_id.max_days_allowed', 'number_of_days')
    def _compute_max_allowed(self):
        for rec in self:
            if rec.holiday_status_id.max_days_allowed > 0:
                max_leave = rec.holiday_status_id.max_days_allowed
                if rec.number_of_days > max_leave:
                    raise ValidationError(
                        _('You are not allowed to request leave greater than %s days' % max_leave))


    def open_leave_payment_wiz(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leave Payment',
            'res_model': 'hr.leave.payment',
            'view_mode': 'form',
            'target': 'new',
        }


    def action_open_entry(self):
        self.ensure_one()
        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form'
        }

    def _validate_leave_request(self):
        """ Validate time off requests
        by creating a calendar event and a resource time off. """
        holidays = self.filtered("employee_id")
        holidays._create_resource_leave()
        meeting_holidays = holidays.filtered(lambda l: l.holiday_status_id.create_calendar_meeting)
        meetings = self.env['calendar.event']
        if meeting_holidays:
            meeting_values_for_user_id = meeting_holidays._prepare_holidays_meeting_values()
            Meeting = self.env['calendar.event']
            for user_id, meeting_values in meeting_values_for_user_id.items():
                # Add sudo to avoid exception
                meetings += Meeting.sudo().with_user(user_id or self.env.uid).with_context(
                                allowed_company_ids=[],
                                no_mail_to_attendees=True,
                                calendar_no_videocall=True,
                                active_model=self._name
                            ).sudo().create(meeting_values)
        Holiday = self.env['hr.leave']
        for meeting in meetings:
            Holiday.browse(meeting.res_id).meeting_id = meeting

        for holiday in holidays:
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            notify_partner_ids = holiday.employee_id.user_id.partner_id.ids
            holiday.message_post(
                body=_(
                    'Your %(leave_type)s planned on %(date)s has been accepted',
                    leave_type=holiday.holiday_status_id.display_name,
                    date=utc_tz.replace(tzinfo=None)
                ),
                partner_ids=notify_partner_ids)
