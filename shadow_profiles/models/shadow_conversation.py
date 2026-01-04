from odoo import models, fields, api


class ShadowConversation(models.Model):
    _name = 'shadow.conversation'
    _description = 'Shadow Profile Conversation'
    _order = 'timestamp desc, id desc'

    shadow_profile_id = fields.Many2one(
        'shadow.profile',
        string='Shadow Profile',
        required=True,
        ondelete='cascade',
        index=True
    )
    channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('messenger', 'Messenger'),
        ('instagram', 'Instagram'),
        ('telegram', 'Telegram'),
        ('website', 'Website'),
        ('phone', 'Phone'),
    ], string='Channel', required=True, index=True)
    message = fields.Text(string='Message', required=True)
    direction = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ], string='Direction', required=True, default='incoming')
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, index=True)
    agent_id = fields.Many2one('res.users', string='Agent', ondelete='set null')
    is_ai_response = fields.Boolean(string='AI Response', default=False)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Update last_contact_date on shadow profile
        if record.shadow_profile_id:
            record.shadow_profile_id.write({'last_contact_date': record.timestamp})
        return record
