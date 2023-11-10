from odoo import api, fields, models, _
import base64
import logging

_logger = logging.getLogger(__name__)
from odoo.exceptions import  UserError


class ChooseDeliveryPackage(models.TransientModel):
    _inherit = "choose.delivery.package"

    length_postex = fields.Float(string="Length")
    width_postex = fields.Float(string="Width")
    height_postex = fields.Float(string="Height")

    @api.onchange('delivery_package_type_id')
    def getting_len_wid_height(self):
        self.width_postex = self.delivery_package_type_id.width
        self.height_postex = self.delivery_package_type_id.height
        self.length_postex = self.delivery_package_type_id.packaging_length


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[
        ('postex', 'POSTEX'),
    ]
        , ondelete={'postex': 'cascade'}
    )

    # delivery_type = fields.Selection(selection_add = [('wepik','Wepik')])
    postex_product_group_id = fields.Many2one(comodel_name='postex.product.group', string='POSTEX Product Group')
    postex_product_type_id = fields.Many2one(comodel_name='postex.product.type', string='POSTEX Product Type')
    postex_payment_method_id = fields.Many2one(comodel_name='postex.payment.method', string='POSTEX Payment Method')
    postex_service_id = fields.Many2one(comodel_name='postex.service', string='POSTEX Service')

    @api.model
    def create(self, vals):
        if vals.get("delivery_type", False) and vals["delivery_type"] == "postex" and vals.get("uom_id", False):
            uom_obj = self.env["uom.uom"].browse(vals["uom_id"])
            if uom_obj and uom_obj.name.upper() not in ["LB", "LB(S)", "KG", "KG(S)"]:
                raise UserError(
                    _("POSTEX Shipping support weight in KG and LB only. Select Odoo Product UoM accordingly."))
        if vals.get("delivery_type", False) and vals["delivery_type"] == "postex" and vals.get("delivery_uom", False):
            if vals["delivery_uom"] not in ["LB", "KG"]:
                raise UserError(_("POSTEX Shipping support weight in KG and LB only. Select API UoM accordingly."))
        return super(DeliveryCarrier, self).create(vals)

    def write(self, vals):
        for rec in self:
            if self.delivery_type == "postex" and vals.get("uom_id", False):
                uom_obj = self.env["uom.uom"].browse(vals["uom_id"])
                if uom_obj and uom_obj.name.upper() not in ["LB", "LB(S)", "KG", "KG(S)"]:
                    raise UserError(
                        _("POSTEX Shipping support weight in KG and LB only. Select Odoo Product UoM accordingly."))
            if self.delivery_type == "postex" and vals.get("delivery_uom", False):
                if vals["delivery_uom"] not in ["LB", "KG"]:
                    raise UserError(_("POSTEX Shipping support weight in KG and LB only. Select API UoM accordingly."))
        return super(DeliveryCarrier, self).write(vals)


class WkShippingProductType(models.Model):
    _name = "postex.product.type"
    _description = "POSTEX product type"

    name = fields.Char(string="Name", required=1)
    code = fields.Char(string="Code", required=1)
    is_dutiable = fields.Boolean(string="Dutiable Product")
    description = fields.Text(string="Full Description")


class WkShippingService(models.Model):
    _name = "postex.service"
    _description = "POSTEX Service"

    name = fields.Char(string="Name", required=1)
    code = fields.Char(string="Code", required=1)
    description = fields.Text(string="Full Description")


class WkShippingProductGroup(models.Model):
    _name = "postex.product.group"
    _description = "POSTEX product group"

    name = fields.Char(string="Name", required=1)
    code = fields.Char(string="Code", required=1)
    description = fields.Text(string="Full Description")


class WkShippingPaymentMethod(models.Model):
    _name = "postex.payment.method"
    _description = "POSTEX product method"

    name = fields.Char(string="Name", required=1)
    code = fields.Char(string="Code", required=1)
    description = fields.Text(string="Full Description")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    make_postex_hit = fields.Boolean(string="POSTEX Label Make")
    return_label_postex = fields.Boolean(string="POSTEX Label Return")

    postex_shipping_label = fields.Char(string="POSTEX Shipping Label", copy=False)
    multi_ship = fields.Boolean(string="Create Seperate Shipment for Every Package", default=True)

    def return_labeling_wepik(self):
        if self.carrier_id:
            self.carrier_id.postex_send_shipping(self)

    def get_postex_shipping_label(self, Label, Shipment):
        for record in self:
            attachments = []
            for item in range(len(Label)):
                attachments.append(('postex_' + Shipment[item] + '.pdf', base64.b64decode(Label[item])))
                msg = "Label generated For POSTEX Shipment "

            if attachments:
                record.message_post(body=msg, subject="Label For POSTEX Shipment", attachments=attachments)
                return True


class ProductPackaging(models.Model):
    _inherit = 'stock.package.type'
    package_carrier_type = fields.Selection(
        selection_add=[('postex', 'POSTEX')])
