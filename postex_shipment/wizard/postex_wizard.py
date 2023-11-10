# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################

from odoo import api, fields, models, _
import logging
from odoo.exceptions import Warning, ValidationError, UserError
import urllib
import xml.etree.ElementTree as etree

_logger = logging.getLogger(__name__)

delivery_uom_list = [('LB', 'LB'), ('KG', 'KG')]


def unicode_to_string(text):
    try:
        text = urllib.parse.unquote_plus(text.encode('utf8'))
        return text
    except Exception as e:
        return text


class POSTEXWizard(models.TransientModel):
    _name = "postex.wizard"
    _description = "POSTEX wizard"

    @api.model
    def _get_active_id(self):
        if self._context.get('active_model') and self._context["active_model"] == "stock.picking":
            active_id = self._context.get('active_id')
        else:
            active_id = self.env["stock.picking"]
        return active_id

    @api.model
    def get_country_code(self):
        country_list = []
        country_objs = self.env["res.country"].search([])
        for country in country_objs:
            country_list.append((str(country.code), country.name))
        return country_list

    @api.model
    def get_postex_product_type(self):
        postex_product_type = []
        postex_product_type_objs = self.env["postex.product.type"].search([])
        for product_type in postex_product_type_objs:
            postex_product_type.append((str(product_type.code), str(product_type.name)))
        return postex_product_type

    @api.model
    def get_postex_service(self):
        postex_service = []
        postex_service_objs = self.env["postex.service"].search([])
        for service in postex_service_objs:
            postex_service.append((str(service.code), str(service.name)))
        return postex_service

    @api.model
    def get_postex_payment_method(self):
        postex_payment_method = []
        postex_payment_method_objs = self.env["postex.payment.method"].search([])
        for payment_method in postex_payment_method_objs:
            postex_payment_method.append((str(payment_method.code), str(payment_method.name)))
        return postex_payment_method

    @api.model
    def get_courrency_code(self):
        courrency_list = []
        courrency_objs = self.env["res.currency"].search(['|', ('active', '=', True), ('active', '=', False)])
        for currency in courrency_objs:
            courrency_list.append((str(currency.name), str(currency.name)))
        return courrency_list

    @api.model
    def get_partner_title(self):
        title_list = []
        title_objs = self.env["res.partner.title"].search([])
        for title in title_objs:
            title_list.append((str(title.shortcut), str(title.shortcut)))
        return title_list

    delivery_uom = fields.Selection(selection=delivery_uom_list, string='UoM')

    # Fields For sender
    sender_name = fields.Char(string="Sender Name")
    sender_title = fields.Selection("get_partner_title", string="Sender Title")
    sender_company_name = fields.Char(string="Sender Company Name")
    sender_phone1 = fields.Char(string="Sender Phone1")
    sender_phone1_ext = fields.Char(string="Sender Extension")
    sender_phone2 = fields.Char(string="Sender Phone2")
    sender_phone2_ext = fields.Char(string="Sender Extension 2")
    sender_fax_number = fields.Char(string="Sender Fax Number")
    sender_mobile = fields.Char(string="Sender Mobile")
    sender_email = fields.Char(string="Sender Email")
    sender_street1 = fields.Char(string="Sender Line 1")
    sender_street2 = fields.Char(string="Sender Line 2")
    sender_street3 = fields.Char(string="Sender Line 3")
    sender_city = fields.Char(string="Sender City")
    sender_state = fields.Char(string="Sender State or Province Code")
    sender_zip = fields.Char(string="Sender Post Code")
    sender_country = fields.Selection("get_country_code", string="Sender Country")

    # Fields for receiver(consignee)
    receiver_name = fields.Char(string="Receiver Name")
    receiver_title = fields.Selection("get_partner_title", string="Receiver Title")
    receiver_company_name = fields.Char(string="Receiver Company Name")
    receiver_phone1 = fields.Char(string="Receiver Phone1")
    receiver_phone1_ext = fields.Char(string="Receiver Extension")
    receiver_phone2 = fields.Char(string="Receiver Phone2")
    receiver_phone2_ext = fields.Char(string="Receiver Extension 2")
    receiver_fax_number = fields.Char(string="Receiver Fax Number")
    receiver_mobile = fields.Char(string="Receiver Mobile")
    receiver_email = fields.Char(string="Receiver Email")
    receiver_street1 = fields.Char(string="Receiver Line 1")
    receiver_street2 = fields.Char(string="Receiver Line 2")
    receiver_street3 = fields.Char(string="Receiver Line 3")
    receiver_city = fields.Char(string="Receiver City")
    receiver_state = fields.Char(string="Receiver State or Province Code")
    receiver_zip = fields.Char(string="Receiver Post Code")
    receiver_country = fields.Selection("get_country_code", string="Receiver Country")

    # Shipment Details
    sender_multi_ship = fields.Boolean(string="Create Multi Shipments for Every Package", default=True)
    total_weight = fields.Float(string="Total Weight")
    total_qty = fields.Integer(string="Total Quantity")
    comments = fields.Char(string="Comments")
    pickup_location = fields.Char(string="Pickup Location")
    operation_instaruction = fields.Char(string="Operation Instructions")
    shipment_ref1 = fields.Char(string="Shipment Reference 1")
    shipment_ref2 = fields.Char(string="Shipment Reference 2")
    product_type = fields.Selection("get_postex_product_type", string="Product Type")
    service_type = fields.Selection("get_postex_service", string="Service Type")
    payment_type = fields.Selection("get_postex_payment_method", string="Payment Type")
    description_of_goods = fields.Char(string="Description Of Goods")
    cod_amount = fields.Float(string="COD Amount")
    cod_currency = fields.Selection("get_courrency_code", string="Currency For COD Amount",
                                    default=lambda self: self.env.user.company_id.currency_id.name)
    custom_amount = fields.Float(string="Custom Amount")
    custome_currency = fields.Selection("get_courrency_code", string="Currency For Custom Amount",
                                        default=lambda self: self.env.user.company_id.currency_id.name)
    insurance_amount = fields.Float(string="Insurance Amount")
    insurance_currency = fields.Selection("get_courrency_code", string="Currency For Insurance Amount",
                                          default=lambda self: self.env.user.company_id.currency_id.name)
    collect_amount = fields.Float(string="Collect Amount")
    collect_currency = fields.Selection("get_courrency_code", string="Currency For Collect Amount",
                                        default=lambda self: self.env.user.company_id.currency_id.name)
    cash_additional_amount = fields.Float(string="Cash Additional Amount")
    cash_additional_currency = fields.Selection("get_courrency_code", string="Currency For Cash Additional Amount",
                                                default=lambda self: self.env.user.company_id.currency_id.name)
    consienment_length = fields.Integer(string="Length")
    consienment_width = fields.Integer(string="Width")
    consienment_height = fields.Integer(string="Height")

    picking_id = fields.Many2one('stock.picking', string="Picking", default=_get_active_id, required=1)

    is_product_type_is_dutiable = fields.Boolean(string="Dutiable Service", compute="get_product_type_dutiable")

    def apply(self):
        self.ensure_one()
        ctx = self._context.copy()
        if self.service_type == "CODS" and self.cod_amount <= 0.0:
            raise UserError(_('COD Amount must be grater than 0.0 for Service Type "Cash On Delivery".'))
        if self.is_product_type_is_dutiable and self.custom_amount <= 0.0:
            raise UserError(
                _('Custom Amount must be grater than 0.0 for Product type of "Dutiable". Product type "PPX, DPX, GPX, EPX" are dutiable.'))

        picking_obj = self.env["stock.picking"].browse(self._context["active_id"]) if self._context.get(
            'active_model') and self._context["active_model"] == "stock.picking" and self._context.get('active_id') else \
        self.env["stock.picking"]
        vals = {
            # Sender Details
            "sender_name": self.sender_name,
            "sender_title": self.sender_title,
            "sender_company_name": self.sender_company_name,
            "sender_phone1": self.sender_phone1,
            "sender_phone1_ext": self.sender_phone1_ext,
            'sender_phone2': "",
            "sender_phone2_ext": self.sender_phone2_ext,
            "sender_fax_number": self.sender_fax_number,
            "sender_mobile": self.sender_mobile,
            "sender_email": self.sender_email,
            "sender_street1": self.sender_street1,
            "sender_street2": self.sender_street2,
            "sender_street3": self.sender_street3,
            "sender_city": self.sender_city,
            "sender_state": self.sender_state,
            "sender_zip": self.sender_zip,
            "sender_country": self.sender_country,

            # Receiver Details
            "receiver_name": self.receiver_name,
            "receiver_title": self.receiver_title,
            "receiver_company_name": self.receiver_company_name,
            "receiver_phone1": self.receiver_phone1,
            "receiver_phone1_ext": self.receiver_phone1_ext,
            "receiver_phone2": self.receiver_phone2,
            "receiver_phone2_ext": self.receiver_phone2_ext,
            "receiver_fax_number": self.receiver_fax_number,
            "receiver_mobile": self.receiver_mobile,
            "receiver_email": self.receiver_email,
            "receiver_street1": self.receiver_street1,
            "receiver_street2": self.receiver_street2,
            "receiver_street3": self.receiver_street3,
            "receiver_city": self.receiver_city,
            "receiver_state": self.receiver_state,
            "receiver_zip": self.receiver_zip,
            "receiver_country": self.receiver_country,

            # Shipment Details
            "sender_multi_ship": self.sender_multi_ship,
            "total_weight": self.total_weight,
            "total_qty": self.total_qty,
            "comments": self.comments,
            "pickup_location": self.pickup_location,
            "operation_instaruction": self.operation_instaruction,
            "shipment_ref1": self.shipment_ref1,
            "shipment_ref2": self.shipment_ref2,
            "product_type": self.product_type,
            "service_type": self.service_type,
            "payment_type": self.payment_type,
            "description_of_goods": self.description_of_goods,
            "cod_amount": self.cod_amount,
            "cod_currency": self.cod_currency,
            "custom_amount": self.custom_amount,
            "custome_currency": self.custome_currency,
            "insurance_amount": self.insurance_amount,
            "insurance_currency": self.insurance_currency,
            "collect_amount": self.collect_amount,
            "collect_currency": self.collect_currency,
            "cash_additional_amount": self.cash_additional_amount,
            "cash_additional_currency": self.cash_additional_currency,
            'consienment_length': self.consienment_length,
            'consienment_width': self.consienment_width,
            'consienment_height': self.consienment_height,

            # Picking Id
            "picking_id": picking_obj,
            "delivery_uom": self.delivery_uom,
        }
        return picking_obj.with_context({"Testing": True, 'vals_for_shipping': vals}).send_to_shipper()

    @api.depends('product_type')
    def get_product_type_dutiable(self):
        if self.product_type:
            product_type_obj = self.env["postex.product.type"].search([("code", "=", self.product_type)], limit=1)
            self.is_product_type_is_dutiable = product_type_obj.is_dutiable

