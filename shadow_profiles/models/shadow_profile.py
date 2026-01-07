from odoo import models, fields, api


class ShadowProfile(models.Model):
    _name = 'shadow.profile'
    _description = 'Shadow Profile'
    _order = 'last_contact_date desc, id desc'

    name = fields.Char(string='Name', required=True, index=True)
    phone = fields.Char(string='Phone', index=True)
    email = fields.Char(string='Email')

    # Social IDs
    facebook_id = fields.Char(string='Facebook ID', index=True)
    instagram_id = fields.Char(string='Instagram ID', index=True)
    whatsapp_id = fields.Char(string='WhatsApp ID', index=True)
    telegram_id = fields.Char(string='Telegram ID', index=True)
    twitter_id = fields.Char(string='Twitter ID')

    # Profile Data
    profile_pic = fields.Char(string='Profile Picture URL')
    interests = fields.Text(string='Interests')
    location = fields.Char(string='Location')
    language = fields.Char(string='Language', default='ar')

    # Status & Tracking
    status = fields.Selection([
        ('anonymous', 'Anonymous'),
        ('qualified', 'Qualified'),
        ('pending_registration', 'Pending Registration'),
        ('registered', 'Registered'),
    ], string='Status', default='anonymous', index=True, required=True)

    source_channel = fields.Selection([
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('website', 'Website'),
        ('phone', 'Phone'),
        ('other', 'Other'),
    ], string='Source Channel', default='other', index=True)

    # Dates
    first_contact_date = fields.Datetime(string='First Contact Date', default=fields.Datetime.now)
    last_contact_date = fields.Datetime(string='Last Contact Date')
    converted_date = fields.Datetime(string='Converted Date')

    # Conversion
    is_converted = fields.Boolean(string='Is Converted', default=False, index=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='set null', index=True)

    # Stats
    message_count = fields.Integer(string='Message Count', default=0)
    promo_code = fields.Char(string='Promo Code')

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
            vals['status'] = 'registered'
            vals['converted_date'] = fields.Datetime.now()
        return super().write(vals)

    def action_qualify(self):
        """Mark shadow profile as qualified"""
        self.write({'status': 'qualified'})

    def action_send_registration(self):
        """Mark as pending registration"""
        self.write({'status': 'pending_registration'})

    def action_convert_to_partner(self):
        """Convert shadow profile to res.partner"""
        self.ensure_one()
        if self.partner_id:
            return self.partner_id

        partner_vals = {
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'comment': self.notes,
        }
        partner = self.env['res.partner'].create(partner_vals)
        self.write({
            'partner_id': partner.id,
            'is_converted': True,
            'status': 'registered',
            'converted_date': fields.Datetime.now(),
        })
        return partner

    @api.model
    def find_or_create(self, platform, platform_id, name=None):
        """Find existing shadow profile or create new one"""
        field_map = {
            'whatsapp': 'whatsapp_id',
            'facebook': 'facebook_id',
            'instagram': 'instagram_id',
            'telegram': 'telegram_id',
        }
        field_name = field_map.get(platform)
        if not field_name:
            return False

        # Search for existing
        profile = self.search([(field_name, '=', platform_id)], limit=1)
        if profile:
            profile.write({'last_contact_date': fields.Datetime.now()})
            return profile

        # Create new
        vals = {
            'name': name or f'{platform}_{platform_id}',
            field_name: platform_id,
            'source_channel': platform,
            'status': 'anonymous',
        }
        return self.create(vals)

    @api.model
    def search_by_identifier(self, identifier):
        """Search by phone or any social ID"""
        domain = [
            '|', '|', '|', '|', '|',
            ('phone', '=', identifier),
            ('whatsapp_id', '=', identifier),
            ('facebook_id', '=', identifier),
            ('instagram_id', '=', identifier),
            ('telegram_id', '=', identifier),
            ('email', '=', identifier),
        ]
        return self.search(domain, limit=1)

    def to_dict(self):
        """Convert to dictionary for API response"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'status': self.status,
            'whatsapp_id': self.whatsapp_id,
            'facebook_id': self.facebook_id,
            'instagram_id': self.instagram_id,
            'telegram_id': self.telegram_id,
            'location': self.location,
            'interests': self.interests,
            'source_channel': self.source_channel,
            'is_converted': self.is_converted,
            'partner_id': self.partner_id.id if self.partner_id else None,
            'message_count': self.message_count,
            'first_contact_date': self.first_contact_date.isoformat() if self.first_contact_date else None,
            'last_contact_date': self.last_contact_date.isoformat() if self.last_contact_date else None,
        }
