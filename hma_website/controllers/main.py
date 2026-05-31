# -*- coding: utf-8 -*-
import re
import logging
from markupsafe import Markup, escape
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Input validation constants ────────────────────────────────────────────────
VALID_CATEGORIES = frozenset({'all', 'cookware', 'dinnerware', 'tea', 'storage', 'chinbull'})
EMAIL_RE = re.compile(r'^[^@\s]{1,64}@[^@\s]{1,255}$')
MAX_FIELD_LEN = 500   # characters — applied to all free-text form inputs


def _sanitize_str(value, max_len=MAX_FIELD_LEN):
    """Strip, truncate, and escape a user-supplied string."""
    if not isinstance(value, str):
        return ''
    return str(value).strip()[:max_len]


def _safe_html_body(name, email, phone, subject, message):
    """Build an HTML email body with all user input properly escaped."""
    return Markup(
        '<p><b>الاسم / Name:</b> {name}</p>'
        '<p><b>البريد / Email:</b> {email}</p>'
        '<p><b>الهاتف / Phone:</b> {phone}</p>'
        '<p><b>الموضوع / Subject:</b> {subject}</p>'
        '<p><b>الرسالة / Message:</b></p>'
        '<p style="white-space:pre-wrap">{message}</p>'
    ).format(
        name=escape(name),
        email=escape(email),
        phone=escape(phone),
        subject=escape(subject),
        message=escape(message),
    )


class HMAWebsiteController(http.Controller):

    # ── Home ─────────────────────────────────────────────────────────────────
    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def index(self, **kwargs):
        featured = request.env['hma.product'].sudo().search(
            [('available', '=', True)], limit=6
        )
        return request.render('hma_website.page_index', {
            'featured_products': featured,
        })

    # ── About ────────────────────────────────────────────────────────────────
    @http.route('/about', type='http', auth='public', website=True, sitemap=True)
    def about(self, **kwargs):
        return request.render('hma_website.page_about', {})

    # ── Products listing ─────────────────────────────────────────────────────
    @http.route('/products', type='http', auth='public', website=True, sitemap=True)
    def products(self, category=None, **kwargs):
        # Whitelist-validate the category parameter — reject anything unexpected
        safe_cat = category if category in VALID_CATEGORIES else 'all'

        domain = [('available', '=', True)]
        if safe_cat and safe_cat != 'all':
            domain.append(('category', '=', safe_cat))

        products = request.env['hma.product'].sudo().search(domain)

        categories = [
            ('all',        'الكل',          'All'),
            ('cookware',   'أطقم الطهي',    'Cookware'),
            ('dinnerware', 'أطقم السفرة',   'Dinnerware'),
            ('tea',        'شاي وقهوة',     'Tea & Coffee'),
            ('storage',    'التخزين',       'Storage'),
            ('chinbull',   'Chinbull حصري', 'Chinbull'),
        ]
        return request.render('hma_website.page_products', {
            'products': products,
            'categories': categories,
            'active_cat': safe_cat,
        })

    # ── Product detail ────────────────────────────────────────────────────────
    @http.route(
        '/products/<int:product_id>',
        type='http', auth='public', website=True, sitemap=False
    )
    def product_detail(self, product_id, **kwargs):
        # product_id is already typed as int by the route converter
        product = request.env['hma.product'].sudo().browse(product_id)
        if not product.exists() or not product.available:
            return request.not_found()

        related = request.env['hma.product'].sudo().search([
            ('category', '=', product.category),
            ('id', '!=', product.id),
            ('available', '=', True),
        ], limit=3)

        return request.render('hma_website.page_product_detail', {
            'product': product,
            'related': related,
        })

    # ── Chinbull ──────────────────────────────────────────────────────────────
    @http.route('/chinbull', type='http', auth='public', website=True, sitemap=True)
    def chinbull(self, **kwargs):
        cb_products = request.env['hma.product'].sudo().search([
            ('category', '=', 'chinbull'),
            ('available', '=', True),
        ])
        return request.render('hma_website.page_chinbull', {
            'cb_products': cb_products,
        })

    # ── Wholesale ─────────────────────────────────────────────────────────────
    @http.route('/wholesale', type='http', auth='public', website=True, sitemap=True)
    def wholesale(self, **kwargs):
        return request.render('hma_website.page_wholesale', {})

    # ── Location ──────────────────────────────────────────────────────────────
    @http.route('/location', type='http', auth='public', website=True, sitemap=True)
    def location(self, **kwargs):
        return request.render('hma_website.page_location', {})

    # ── Contact GET ───────────────────────────────────────────────────────────
    @http.route('/contact', type='http', auth='public', website=True, sitemap=True)
    def contact(self, **kwargs):
        return request.render('hma_website.page_contact', {
            'success': False,
            'error': None,
        })

    # ── Contact POST ──────────────────────────────────────────────────────────
    @http.route(
        '/contact/submit',
        type='http', auth='public', website=True,
        methods=['POST'], csrf=True,
    )
    def contact_submit(self, **post):
        # ── Sanitize all inputs ──────────────────────────────────────────────
        name    = _sanitize_str(post.get('name', ''))
        email   = _sanitize_str(post.get('email', ''), max_len=254)
        phone   = _sanitize_str(post.get('phone', ''), max_len=30)
        subject = _sanitize_str(post.get('subject', ''))
        message = _sanitize_str(post.get('message', ''), max_len=2000)

        # ── Basic validation ────────────────────────────────────────────────
        error = None
        if not name:
            error = 'الاسم مطلوب / Name is required'
        elif email and not EMAIL_RE.match(email):
            error = 'البريد الإلكتروني غير صحيح / Invalid email address'

        if error:
            return request.render('hma_website.page_contact', {
                'success': False,
                'error': error,
                # Preserve filled values so user doesn't retype
                'form_values': {
                    'name': name, 'email': email,
                    'phone': phone, 'subject': subject, 'message': message,
                },
            })

        # ── Send email with escaped HTML body ────────────────────────────────
        try:
            request.env['mail.mail'].sudo().create({
                'subject': f'[HMA Website] {subject or "استفسار جديد"}',
                'body_html': _safe_html_body(name, email, phone, subject, message),
                'email_to': 'info@HMA.net',
                'email_from': email if email and EMAIL_RE.match(email) else 'website@HMA.net',
            }).send()
        except Exception:
            _logger.exception('HMA contact form: failed to send email')

        return request.render('hma_website.page_contact', {
            'success': True,
            'error': None,
        })

    # ── Sitemap page ──────────────────────────────────────────────────────────
    @http.route('/sitemap', type='http', auth='public', website=True, sitemap=False)
    def sitemap_page(self, **kwargs):
        products = request.env['hma.product'].sudo().search([
            ('available', '=', True)
        ])
        return request.render('hma_website.page_sitemap', {'products': products})
