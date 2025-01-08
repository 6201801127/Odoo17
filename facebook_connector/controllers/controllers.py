# -*- coding: utf-8 -*-
# from odoo import http


# class FacebookConnector(http.Controller):
#     @http.route('/facebook_connector/facebook_connector', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/facebook_connector/facebook_connector/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('facebook_connector.listing', {
#             'root': '/facebook_connector/facebook_connector',
#             'objects': http.request.env['facebook_connector.facebook_connector'].search([]),
#         })

#     @http.route('/facebook_connector/facebook_connector/objects/<model("facebook_connector.facebook_connector"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('facebook_connector.object', {
#             'object': obj
#         })

