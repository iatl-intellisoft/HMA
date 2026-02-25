# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL International Pvt. Ltd.
#    Copyright (C) 2018-TODAY Tech-Receptives(<http://www.iatl-sd.com>).
#
###############################################################################
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    custody_account_id = fields.Many2one('account.account', string='Account')
    clearance_journal = fields.Many2one('account.journal', string='Clearance Journal')
    # secure_sequence_id = fields.Many2one('ir.sequence',
    #                                      help='Sequence to use to ensure the securisation of data',
    #                                      check_company=True,
    #                                      readonly=True, copy=False)
    #
    #
    #
    # def create(self, vals):
    #     if 'secure_sequence_id' not in vals or not vals['secure_sequence_id']:
    #         seq = self.env['ir.sequence'].sudo().create({
    #             'name': _('Securisation of %s') % (vals['name']),
    #             'prefix': '',
    #             'suffix': '',
    #             'padding': 3,
    #             'company_id': '',
    #         })
    #         vals['secure_sequence_id'] = seq.id
    #     return super(ResCompany, self).create(vals)


class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    custody_account_id = fields.Many2one('account.account', string='Account', related='company_id.custody_account_id',
                                         readonly=False)
    clearance_journal = fields.Many2one('account.journal', string='Clearance Journal',
                                        related='company_id.clearance_journal',
                                        readonly=False)

    # secure_sequence_id = fields.Many2one('ir.sequence',
    #                                      help='Sequence to use to ensure the securisation of data',
    #                                      check_company=True,
    #                                      related='company_id.secure_sequence_id',
    #                                      readonly=True, copy=False)

