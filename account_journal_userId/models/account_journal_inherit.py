from odoo import api, fields, models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    user_id = fields.Many2one(
        'res.users',
        string='إسم المستخدم'
    )