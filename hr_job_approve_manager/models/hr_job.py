from odoo import models, fields, api
from odoo.exceptions import UserError


class HrJob(models.Model):
    _inherit = 'hr.job'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting Manager Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='approved', tracking=True)

    def action_submit(self):
        self.state = 'waiting_approval'

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):  
        self.unlink()

