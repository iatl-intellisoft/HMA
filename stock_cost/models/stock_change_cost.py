# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class StockChangeForeignCost(models.Model):
    _name = "stock.change.foreign.cost"
    _description = "Change Foreign Standard Price"

    line_ids = fields.One2many('stock.change.foreign.cost.lines','stock_change_cost_id', string="Products")
    date =fields.Date(string="Date",default=fields.Date.today())
    accounting_date = fields.Date(string="Accounting Date")
    name = fields.Char(string="Reference")
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Validated')],
        copy=False, index=True, readonly=True,
        default='draft')
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, index=True, required=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.change.foreign.standard.price'))



    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("You can not confitm without products"))
            rec.write({'state': 'confirm'})
        return True


    def action_validate(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("You can not confitm without products"))
            # rec.do_change_standard_price()
            for line in rec.line_ids:
                line.product_id.write({'foreign_standard_price': line.new_foreign_standard_price})
            rec.write({'state': 'done'})
        return True


    def action_cancel_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})
        return True


    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})
        return True


    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("You can not delete no draft record!"))
        return super(StockChangeForeignCost, self).unlink()


    def do_change_standard_price(self):
        """ Changes the Foreign Standard Price of Product and creates an account move accordingly."""
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        move = False
        for line in self.line_ids:
            product = line.product_id
            new_price = line.new_foreign_standard_price
            account_id = line.counterpart_account_id.id
            product_accounts = {p.id: p.product_tmpl_id.get_product_accounts() for p in product}

            company_currency = product.currency_id
            force_currency_id = product.force_currency_id
            new_foreign_price = 0
            currency_id = False
            
            if not force_currency_id:
                raise UserError(_("The product %s has not force currency.")%product.name)
            if force_currency_id and force_currency_id != company_currency:
                new_company_price = force_currency_id.with_context(date=fields.Date.today()).compute(abs(new_price), company_currency)
            else:
                new_company_price = new_price
            diff = product.foreign_standard_price - new_price
            amount_currency = 0
            line_ids = []
            
            if float_is_zero(diff, precision_rounding=product.currency_id.rounding):
                raise UserError(_("No difference between the standard price and the new price."))
            if not product_accounts[product.id].get('stock_valuation', False):
                raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
            qty_available = product.qty_available
            if qty_available:
                # Accounting Entries
                if diff * qty_available > 0:
                    debit_account_id = account_id
                    credit_account_id = product_accounts[product.id]['stock_valuation'].id
                else:
                    debit_account_id = product_accounts[product.id]['stock_valuation'].id
                    credit_account_id = account_id

                if force_currency_id and force_currency_id != company_currency:
                    amount = force_currency_id.with_context(date=fields.Date.today()).compute(abs(diff * qty_available), company_currency)
                    amount_currency = abs(diff * qty_available)
                    currency_id = force_currency_id

                else:
                    amount = abs(diff * qty_available)

                line_ids = [(0, 0, {
                        'name': _('%s changed cost from %s to %s - %s') % (self.env.user.name, product.standard_price, new_price, product.display_name),
                        'account_id': debit_account_id,
                        'debit': abs(amount),
                        'credit': 0,
                        'product_id': product.id,
                        'amount_currency': amount_currency,
                        'currency_id': currency_id and currency_id.id or False,
                    }), (0, 0, {
                        'name': _('%s changed cost from %s to %s - %s') % (self.env.user.name, product.standard_price, new_price, product.display_name),
                        'account_id': credit_account_id,
                        'debit': 0,
                        'credit': abs(amount),
                        'product_id': product.id,
                        'amount_currency': amount_currency * -1,
                        'currency_id': currency_id and currency_id.id or False,
                    })]

                if not move:
                    move_vals = {
                    'journal_id': product_accounts[product.id]['stock_journal'].id,
                    'ref': "Update Product Cost"+"-"+str(line.stock_change_cost_id.name),
                    'line_ids': line_ids,
                    'date':line.stock_change_cost_id.accounting_date or line.stock_change_cost_id.date,
                    }
                    move = AccountMove.with_context(check_move_validity=False).create(move_vals)
                else:
                    for line in line_ids:
                        line[2]['move_id'] = move.id
                        AccountMoveLine.with_context(check_move_validity=False).create(line[2])
            product.write({'standard_price': new_company_price, 'foreign_standard_price': new_price})
        if move:
            move.post()
        return True


class StockChangeForeignCostLine(models.Model):
    _name = "stock.change.foreign.cost.lines"

    stock_change_cost_id = fields.Many2one('stock.change.foreign.cost', string="Change Foreign Cost", 
        ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True,help="Only products with Inventory Valuation equal to Automated will appear here.")
    product_categ_id = fields.Many2one('product.category', string="Product Category")
    foreign_standard_price = fields.Float(string='Foreign Cost', digits='Product Price')
    force_currency_id = fields.Many2one(
        'res.currency',
        'Force Currency',
        help='Use this currency instead of the product company currency')
    new_foreign_standard_price = fields.Float(
        'New Foreign Cost', digits='Product Price', required=True,)
    counterpart_account_id = fields.Many2one(
        'account.account', string="Counter-Part Account",
        domain=[('deprecated', '=', False)])
    counterpart_account_id_required = fields.Boolean(string="Counter-Part Account Required")
    qty_available = fields.Float('Quantity Available')


    @api.onchange('product_id')
    def onchange_product_id(self):
        vals = {'product_categ_id': False, 
        'foreign_standard_price': 0,
        'force_currency_id': False,
        'counterpart_account_id_required': False,
        'counterpart_account_id': False,
        'qty_available': 0,
        }
        if self.product_id:
            vals = {'product_categ_id': self.product_id.categ_id.id, 
                    'foreign_standard_price': self.product_id.foreign_standard_price,
                    'force_currency_id': self.product_id.force_currency_id.id,
                    'counterpart_account_id': self.product_id.property_account_expense_id.id or self.product_id.categ_id.property_account_expense_categ_id.id,
                    'counterpart_account_id_required': bool(self.product_id.valuation == 'real_time'),
                    'qty_available': self.product_id.qty_available
                    
                    }
        return {'value':vals}
        
