from odoo import fields, models, api , _ 
import requests
import os

class FacebookLead(models.Model):
    _name = 'facebook.lead'
    _description = 'Facebook Lead'

    name = fields.Char('Lead Name')
    message = fields.Char('Message')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    facebook_lead_id = fields.Char('Facebook Lead ID')
    create_date = fields.Datetime('Lead Date')
    lead_type = fields.Char('Lead Type')
    picture = fields.Binary(string="Picture")
    facebook_campaign_id = fields.Char('Campaign ID')

    # @api.model
    def post_to_facebook(self):
        """
        Post content to Facebook using Graph API.
        """
        # Fetch the page access token (or use a hardcoded one)
        page_access_token = '1241327046951424|xnehlZIgN1YZCf2fbJ-1YMheT3k'
        page_id = 'A07B9ok-naYUB91k1VvohZT'  # Replace with the actual page ID

        # Check that page_access_token and page_id are valid
        if not page_access_token or not page_id:
            raise Exception("Facebook access token or Page ID is missing.")
        
        # Prepare URL for posting to the page's feed
        url = f'https://www.facebook.com/profile.php?id=61571411397175'
        
        # Prepare the data to send
        data = {
            'message': self.message,  # The message content
            'access_token': page_access_token
        }
        
        # If you're including a picture, it would go like this:
        # If the picture is binary data, you need to upload it as a file.
        if self.picture:
            files = {
                'file': ('lead_picture.png', self.picture, 'image/png')
            }
            response = requests.post(url, data=data, files=files)
        else:
            # Post without picture
            response = requests.post(url, data=data)

        # Check the response status code
        if response.status_code == 200:
            # Successfully posted
            return True
        else:
            # Handle error response
            raise Exception(f"Failed to post to Facebook: {response.text}")

    def action_post_to_facebook(self):
        """
        Trigger the post_to_facebook method from the Odoo UI.
        """
        self.post_to_facebook()
