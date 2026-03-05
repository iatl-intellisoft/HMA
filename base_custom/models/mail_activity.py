from odoo import api, fields, models

class MailActivity(models.Model):

    _inherit = 'mail.activity'
    
    
    create_throw_system = fields.Boolean(string="create throw system")




