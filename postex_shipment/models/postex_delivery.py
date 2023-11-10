from odoo import fields, models, _
import requests
import json
import logging
from odoo.exceptions import ValidationError, UserError
import re
from odoo.exceptions import Warning
import base64

_logger = logging.getLogger(__name__)
try:
    from suds.client import Client
except:
    raise Warning("Please install suds: pip3 install suds-py3")

# shipping_service_live = 'https://stg-api.postex.pk/services/integration/api/order'


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"
    postex_api_token = fields.Char(string="PostEx Token")
    postex_connection_status = fields.Selection([('success', 'Connection Successful'), ('failed', 'Connection Failed')],
                                                string="Connection Status",
                                                readonly=True)
    shipping_service_live = fields.Char(string="Base Url")
    # postex_client_name = fields.Char(string="Picking Name")
    # postex_client_country = fields.Char(string="Picking Country")
    # postex_client_city = fields.Char(string="Picking City")
    # postex_client_zip = fields.Char(string="Picking Zip")
    # postex_client_address = fields.Char(string="Picking Address")
    # postex_id = fields.Char(string="API ID")
    # postex_picking_id = fields.Integer(string="id")
    def get_client_credentials_postex(self):
        headers = {
            'token': self.postex_api_token
        }
        url = self.shipping_service_live + '/v2/get-operational-city'
        response = requests.request('GET', url, headers=headers)
        if response.status_code not in [201, 200]:
            self.postex_connection_status = "failed"
            raise UserError(response.json()['error'])
        self.postex_connection_status = "success"
        existing_cities = self.env['sc_needs.courier.cities'].search([('delivery_carrier_id', '=', self.id)])
        cities_to_delete = existing_cities.filtered(
            lambda city: city.name not in [response_city['operationalCityName'] for response_city in response.json()['dist']])
        if cities_to_delete:
            cities_to_delete.unlink()
        for city in response.json()['dist']:
            if city['operationalCityName'] not in self.env['sc_needs.courier.cities'].search(
                    [('delivery_carrier_id', '=', self.id)]).mapped('name'):
                self.env['sc_needs.courier.cities'].create({
                    'delivery_carrier_id': self.id,
                    'name': city['operationalCityName']
                })

    def postex_send_shipping(self, pickings, shipping_status=True):  # OWN
        # self.postex_picking_id = str(pickings.id)
        for obj in self:
            packaging_ids = pickings.move_line_ids_without_package
            order = pickings.sale_id if pickings.sale_id else None
            tracking_number = pickings.carrier_tracking_ref
            # try:
            if not tracking_number or not shipping_status:
                response_list = self.create_postex_shipment_order(order, pickings=pickings, packaging_ids=packaging_ids,
                                                                  shipping_status=shipping_status)
                if response_list['dist']['trackingNumber']:
                    pickings.message_post(body="Shipment created successfully")
                    pickings.carrier_tracking_ref = response_list['dist']['trackingNumber']
                    pickings.print_postex_label()
                else:
                    pickings.message_post(body="Shipment unsuccessfully")
            result = [{
                'exact_price': pickings.sale_id.amount_total if pickings.sale_id else 0.00,
                'tracking_number': response_list['dist']['trackingNumber']
            }]
            return result

    def create_postex_shipment_order(self, order, pickings, packaging_ids, shipping_status):
        if self.postex_connection_status == 'success':
            headers = {
                'token': self.postex_api_token,
                'Content-Type': 'application/json'
            }
            price = self.env['sale.order'].search([('picking_ids', '=', pickings.id)]).amount_total
            order_detail = ', '.join(
                [f"{prod.display_name} Quantity: {prod.qty_done}" for prod in pickings.move_line_ids])
            payload = json.dumps({
                "cityName": pickings.partner_id.city,
                "customerName": pickings.partner_id.name,
                "customerPhone": pickings.partner_id.phone,
                "deliveryAddress": pickings.partner_id.contact_address_complete,
                "invoiceDivision": 0,
                "invoicePayment": str(int(price)),
                "items": len(pickings.move_line_ids),
                "orderDetail": order_detail,
                "orderRefNumber": order.name,
                "orderType": "Normal",
                "transactionNotes": "Order Created from Odoo",
                "pickupAddressCode": "001"
            })
            url = self.shipping_service_live + "/v3/create-order"
            response = requests.request('POST', url, data=payload, headers=headers)
            if response.status_code not in [201, 200]:
                raise UserError(response.json()['statusMessage'])

            json_response = response.json()
            # stock_picking_obj = self.env['stock.picking'].search([('id', '=', self.postex_picking_id)])
            # stock_picking_obj.postex_id = json_response['id']

            return json_response
        else:
            raise UserError("Connection is not Successfull with Call Courier. Please Check the credentials.")

    def remove_country_code(self, phone_number):
        phone_number = re.sub(r'^\+\d+', '', phone_number)
        phone_number = re.sub(r'\s+', '', phone_number)
        return phone_number

    def postex_get_return_label(self):
        print('return label postex')
        pass

    def postex_cancel_shipment(self, pickings):
        headers = {
            'token': self.postex_api_token,
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            "trackingNumber": pickings.carrier_tracking_ref
        })
        url = self.shipping_service_live + "/v1/cancel-order"
        response = requests.request("PUT", url, headers=headers, data=payload)
        if response.status_code not in [201, 200]:
            raise UserError(response.json()['error'])
        if response.json()['statusCode'] not in [201, 200]:
            pickings.order_status = "Order has already been Cancelled"
            pickings.payment_status = ""
            return
        pickings.get_tracking_history_postex()
        pickings.payment_status = "not_paid"
        logmessage = (
                _("<b>API RESPONSE : </b>%s") % (
            str(response.json()['statusMessage'])))
        pickings.message_post(body=logmessage)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    postex_id = fields.Char(string="POSTEX ID", readonly=True)
    # postex_order_status = fields.Char(string="PostEx Order Status", readonly=True)
    # postex_payment_status = fields.Selection([('paid', 'Paid'), ('not_paid', 'Not Paid Yet')],
    #                                          string="PostEx Payment Status", readonly=True)
    postex_receipt_number = fields.Char(string="PostEx Receipt Number", readonly=True)

    def get_tracking_history_postex(self):
        if self.carrier_id.delivery_type == 'postex':
            if self.carrier_tracking_ref:
                headers = {
                    'token': self.carrier_id.postex_api_token,
                    'Content-Type': 'application/json'
                }
                url = self.carrier_id.shipping_service_live + '/v1/track-order/' + self.carrier_tracking_ref
                response = requests.request("GET", url, headers=headers)
                if response.status_code not in [201, 200]:
                    raise UserError(response.json()['error'])
                self.order_status = response.json()['dist']['transactionStatus']
            else:
                self.order_status = "No Tracking Reference found against this order."

    def get_payment_status_postex(self):
        if self.carrier_tracking_ref:
            headers = {
                'token': self.carrier_id.postex_api_token,
                'Content-Type': 'application/json'
            }
            url = self.carrier_id.shipping_service_live + '/v1/payment-status/' + self.carrier_tracking_ref
            response = requests.request("GET", url, headers=headers)
            if response.status_code not in [201, 200]:
                raise UserError(response.json()['error'])
            if response.json()['dist']['settle']:
                self.get_tracking_history_postex()
                self.payment_status = "paid"
                self.postex_receipt_number = response.json()['dist']['cprNumber_1']
            else:
                self.payment_status = "not_paid"
        else:
            if not self.carrier_tracking_ref:
                self.order_status = 'Tracking Reference is not updated.'

    def print_postex_label(self):
        headers = {
            'token': self.carrier_id.postex_api_token,
            'Content-Type': 'application/json'
        }
        # id = str(self.postex_id)
        url = self.carrier_id.shipping_service_live + '/v1/get-invoice?trackingNumbers=' + self.carrier_tracking_ref
        payload = {}
        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code not in [200, 201]:
            raise UserError(response.json()['error'])
        pdf = self.env['ir.attachment'].create(
            {
                'name': ('Label-%s.pdf' % (self.carrier_tracking_ref)),
                'type': 'binary',
                'datas': base64.b64encode(response.content).decode('utf-8'),
                'res_model': 'delivery.carrier',
                'res_id': self.id
            })

        logmessage = (
                _("Label created into POSTEX <br/> <b>Tracking Number : </b>%s") % (
            self.carrier_tracking_ref))

        self.message_post(body=logmessage, attachment_ids=[pdf.id])

    def return_postex_label(self):
        headers = {
            'token': self.carrier_id.postex_api_token,
            'Content-Type': 'application/json'
        }
        price = self.env['sale.order'].search([('picking_ids', '=', self.id)]).amount_total
        # order_detail = ', '.join([f"{prod.display_name} Quantity: {prod.qty_done}" for prod in self.move_line_ids])
        payload = json.dumps({
            "cityName": self.partner_id.city,
            "customerName": self.partner_id.name,
            "customerPhone": self.partner_id.phone,
            "deliveryAddress": self.partner_id.contact_address_complete,
            "invoiceDivision": 0,
            "invoicePayment": "0",
            "items": len(self.move_line_ids),
            "orderDetail": "This is a reversal order against the tracking ID: " + self.carrier_tracking_ref,
            "orderRefNumber": self.name,
            "orderType": "Reversed",
            "transactionNotes": "Order Created from Odoo",
            "pickupAddressCode": "003"
        })
        url = self.carrier_id.shipping_service_live + "/v3/create-order"
        response = requests.request('POST', url, data=payload, headers=headers)
        if response.status_code not in [201, 200]:
            raise UserError(response.json()['error'])
        self.message_post(body="Shipment created successfully")
        self.carrier_tracking_ref = response.json()['dist']['trackingNumber']
        logmessage = (
                _("Return Label created into POSTEX <br/> <b>Tracking Number : </b>%s") % (
            self.carrier_tracking_ref))

        self.message_post(body=logmessage)
