# -*- coding:utf-8 -*-

from collections import defaultdict
from datetime import datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class HrLeave(models.Model):
    _inherit = 'hr.leave'

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),  # YTI This state seems to be unused. To remove
        ('confirm', 'To Approve'),
        ('wait_department_manager', 'Waiting Approve Department Manager'),
        ('wait_hr_manager', 'Waiting HR Approval'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], string='Status', readonly=True, tracking=True, copy=False, default='draft',
        help="The status is set to 'To Submit', when a time off request is created." +
             "\nThe status is 'To Approve', when time off request is confirmed by user." +
             "\nThe status is 'Refused', when time off request is refused by manager." +
             "\nThe status is 'Approved', when time off request is approved by manager.")


    def action_approve(self):
        """
        A method to submit loan request.
        """

        super(HrLeave, self).action_approve()
        self.write({
             'state': 'wait_department_manager'

        })
    def action_department_manager(self):
        """
        A method to submit loan request.
        """
        self.write({
             'state': 'wait_hr_manager'
        })

    def action_hr_manager(self):
        """
        A method to submit loan request.
        """
        self.write({
             'state': 'validate'

        })

    def action_validate(self):
        """
        update to create work entry for linked holidays in case holiday_type not employee
        """
        super(HrLeave, self).action_validate()
        # delete preexisting conflicting work_entries
        # self.sudo()._cancel_work_entry_conflict()
        self.filtered(lambda x: x.holiday_type !=
                      'employee').linked_request_ids.sudo()._cancel_work_entry_conflict()

        return True

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    current_leave_state = fields.Selection(compute='_compute_leave_status', string="Current Time Off Status",
        selection=[
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),  # YTI This state seems to be unused. To remove
        ('confirm', 'To Approve'),
        ('wait_department_manager', 'Waiting Approve Department Manager'),
        ('wait_hr_manager', 'Waiting HR Approval'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ])