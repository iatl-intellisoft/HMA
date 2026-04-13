# -*- coding: utf-8 -*-
# from odoo import http


# class SaudiHrOvertime(http.Controller):
#     @http.route('/afag_hr_overtime/afag_hr_overtime/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/afag_hr_overtime/afag_hr_overtime/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('afag_hr_overtime.listing', {
#             'root': '/afag_hr_overtime/afag_hr_overtime',
#             'objects': http.request.env['afag_hr_overtime.afag_hr_overtime'].search([]),
#         })

#     @http.route('/afag_hr_overtime/afag_hr_overtime/objects/<model("afag_hr_overtime.afag_hr_overtime"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('afag_hr_overtime.object', {
#             'object': obj
#         })
