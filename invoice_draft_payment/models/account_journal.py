
from odoo import models, fields, api
from datetime import datetime, timedelta 
from odoo.tools.misc import formatLang

class account_journal(models.Model):
    _inherit = "account.journal"

    post_at_bank= fields.Boolean(string="Set payment Draft", default=True)
