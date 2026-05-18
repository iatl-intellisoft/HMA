# -*- coding: utf-8 -*-
# from odoo import http


# class SaleMultiWarehouse(http.Controller):
#     @http.route('/sale_multi_warehouse/sale_multi_warehouse/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_multi_warehouse/sale_multi_warehouse/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_multi_warehouse.listing', {
#             'root': '/sale_multi_warehouse/sale_multi_warehouse',
#             'objects': http.request.env['sale_multi_warehouse.sale_multi_warehouse'].search([]),
#         })

#     @http.route('/sale_multi_warehouse/sale_multi_warehouse/objects/<model("sale_multi_warehouse.sale_multi_warehouse"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_multi_warehouse.object', {
#             'object': obj
#         })
