# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Users(models.Model):

    _inherit = "res.users"

    def _default_groups(self):
        default_user = self.env.ref('base.group_user', raise_if_not_found=False)
        return default_user

    groups_id = fields.Many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', string='Groups', default=_default_groups)
    department_id = fields.Many2one('hr.department', string='Department')
    allowed_department_ids = fields.Many2many('hr.department', 'rdepartment_users_rel', 'uid', 'department_id', string='Allowed Departments')