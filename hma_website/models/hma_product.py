# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# Allowed category values — used for both Selection field and input whitelist
VALID_CATEGORIES = {'cookware', 'dinnerware', 'tea', 'storage', 'chinbull'}

# Regex for WhatsApp numbers: digits only, 10–15 chars (E.164 without +)
WA_NUMBER_RE = re.compile(r'^\d{10,15}$')


class HmaProduct(models.Model):
    _name = 'hma.product'
    _description = 'HMA Product'
    _rec_name = 'name_ar'
    _order = 'sequence, id'

    name_ar = fields.Char('Name (Arabic)', required=True, translate=False)
    name_en = fields.Char('Name (English)', required=True, translate=False)
    category = fields.Selection([
        ('cookware',   'أطقم الطهي / Cookware'),
        ('dinnerware', 'أطقم السفرة / Dinnerware'),
        ('tea',        'شاي وقهوة / Tea & Coffee'),
        ('storage',    'التخزين / Storage'),
        ('chinbull',   'Chinbull حصري / Chinbull Exclusive'),
    ], string='Category', required=True, index=True)
    cat_label_ar = fields.Char('Category Label (Arabic)')
    cat_label_en = fields.Char('Category Label (English)')
    icon = fields.Char('FontAwesome Icon Class', default='fa fa-box')
    badge = fields.Selection([
        ('new',       'New'),
        ('wholesale', 'Wholesale'),
        ('cb',        'Chinbull'),
    ], string='Badge')
    badge_label_ar = fields.Char('Badge Label (Arabic)')
    badge_label_en = fields.Char('Badge Label (English)')
    desc_ar = fields.Text('Short Description (Arabic)')
    desc_en = fields.Text('Short Description (English)')
    full_desc_ar = fields.Text('Full Description (Arabic)')
    full_desc_en = fields.Text('Full Description (English)')
    avail_label_ar = fields.Char('Availability Label (Arabic)')
    avail_label_en = fields.Char('Availability Label (English)')
    available = fields.Boolean('Available', default=True)
    dark_bg = fields.Boolean('Dark Card Background', default=False)
    wa_number = fields.Char(
        'WhatsApp Number',
        default='249912390982',
        help='Digits only, no + or spaces. E.g. 249912390982',
    )
    sequence = fields.Integer('Sequence', default=10)
    spec_ids = fields.One2many('hma.product.spec', 'product_id', 'Specs')
    feature_ids = fields.One2many('hma.product.feature', 'product_id', 'Features')

    # ── Validation ────────────────────────────────────────────────────────────

    @api.constrains('wa_number')
    def _check_wa_number(self):
        for rec in self:
            if rec.wa_number and not WA_NUMBER_RE.match(rec.wa_number):
                raise ValidationError(
                    'WhatsApp number must contain digits only, 10–15 characters. '
                    f'Got: {rec.wa_number!r}'
                )

    # ── Safe URL helpers (called from QWeb) ───────────────────────────────────

    def get_wa_url(self):
        """Return a safe WhatsApp URL. Falls back to empty string on bad data."""
        self.ensure_one()
        number = self.wa_number or ''
        if WA_NUMBER_RE.match(number):
            return f'https://wa.me/{number}'
        return ''


class HmaProductSpec(models.Model):
    _name = 'hma.product.spec'
    _description = 'HMA Product Spec'
    _rec_name = 'label_ar'
    _order = 'sequence, id'

    product_id = fields.Many2one(
        'hma.product', ondelete='cascade', required=True, index=True
    )
    icon = fields.Char('Icon Class')
    label_ar = fields.Char('Label (Arabic)')
    label_en = fields.Char('Label (English)')
    sequence = fields.Integer(default=10)


class HmaProductFeature(models.Model):
    _name = 'hma.product.feature'
    _description = 'HMA Product Feature'
    _rec_name = 'label_ar'
    _order = 'sequence, id'

    product_id = fields.Many2one(
        'hma.product', ondelete='cascade', required=True, index=True
    )
    icon = fields.Char('Icon Class')
    label_ar = fields.Char('Label (Arabic)')
    label_en = fields.Char('Label (English)')
    sequence = fields.Integer(default=10)
