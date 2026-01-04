from odoo import models, fields, api


class ShadowProfile(models.Model):
    _name = 'shadow.profile'
    _description = 'Shadow Profile'
    _order = 'last_contact_date desc, id desc'

    name = fields.Char(string='Name', required=True, index=True)
    phone = fields.Char(string='Phone')
    facebook_id = fields.Char(string='Facebook ID')
    instagram_id = fields.Char(string='Instagram ID')
    whatsapp_id = fields.Char(string='WhatsApp ID')
    telegram_id = fields.Char(string='Telegram ID')
    interests = fields.Text(string='Interests')
    location = fields.Char(string='Location')
    source_channel = fields.Selection([
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('website', 'Website'),
        ('other', 'Other'),
    ], string='Source Channel', default='other', index=True)
    first_contact_date = fields.Datetime(string='First Contact Date', default=fields.Datetime.now)
    last_contact_date = fields.Datetime(string='Last Contact Date')
    is_converted = fields.Boolean(string='Is Converted', default=False)
    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='set null')
    notes = fields.Text(string='Notes')
    
    # One2many to conversations
    conversation_ids = fields.One2many(
        'shadow.conversation',
        'shadow_profile_id',
        string='Conversations'
    )
    conversation_count = fields.Integer(
        string='Conversations Count',
        compute='_compute_conversation_count'
    )

    @api.depends('conversation_ids')
    def _compute_conversation_count(self):
        for record in self:
            record.conversation_count = len(record.conversation_ids)

    @api.model
    def create(self, vals):
        if not vals.get('first_contact_date'):
            vals['first_contact_date'] = fields.Datetime.now()
        return super().create(vals)

    def write(self, vals):
        if 'partner_id' in vals and vals['partner_id']:
            vals['is_converted'] = True
        return super().write(vals)
