# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):

    @http.route(["/loan/template/<model('hr.loan'):template>"], type='http', auth="public", website=True)
    

    def portal_contract_template(self, template, **post):
        values = {'docs': template,
        }

        return request.render('hr_loan.loan_request_template_id', values)

    
    # @http.route(["/amendmentContract/template/<model('amendment.contract'):template>"], type='http', auth="public", website=True)
    

    # def portal_amendment_contract_template(self, template, **post):
    #     values = {'docs': template,
    #     }

        # return request.render('hr_loan.contract_amendment_portal_template', values)
