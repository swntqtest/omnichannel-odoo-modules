from odoo import models, fields, api


class CCCall(models.Model):
    _name = 'cc.call'
    _description = 'Contact Center Call/Interaction'
    _order = 'start_time desc'

    name = fields.Char(string='Reference', readonly=True, copy=False)

    # Type and channel
    interaction_type = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Type', required=True, default='inbound', index=True)

    channel = fields.Selection([
        ('voice', 'Voice'),
        ('chat', 'Chat'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('messenger', 'Messenger'),
        ('instagram', 'Instagram'),
        ('telegram', 'Telegram'),
    ], string='Channel', required=True, default='voice', index=True)

    # Status
    status = fields.Selection([
        ('queued', 'Queued'),
        ('ringing', 'Ringing'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('abandoned', 'Abandoned'),
        ('transferred', 'Transferred'),
    ], string='Status', default='queued', required=True, index=True)

    # Participants
    agent_id = fields.Many2one(
        'cc.agent',
        string='Agent',
        ondelete='set null',
        index=True
    )
    queue_id = fields.Many2one(
        'cc.queue',
        string='Queue',
        ondelete='set null',
        index=True
    )

    # Contact info
    caller_number = fields.Char(string='Caller Number', index=True)
    caller_name = fields.Char(string='Caller Name')

    # Shadow profile link
    shadow_profile_id = fields.Many2one(
        'shadow.profile',
        string='Shadow Profile',
        ondelete='set null'
    )

    # Partner link
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        ondelete='set null'
    )

    # Times
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now, index=True)
    answer_time = fields.Datetime(string='Answer Time')
    end_time = fields.Datetime(string='End Time')

    # Durations (computed)
    wait_duration = fields.Integer(string='Wait Duration (sec)', compute='_compute_durations', store=True)
    talk_duration = fields.Integer(string='Talk Duration (sec)', compute='_compute_durations', store=True)
    hold_duration = fields.Integer(string='Hold Duration (sec)', default=0)
    total_duration = fields.Integer(string='Total Duration (sec)', compute='_compute_durations', store=True)

    # Notes and disposition
    notes = fields.Text(string='Notes')
    disposition = fields.Selection([
        ('resolved', 'Resolved'),
        ('follow_up', 'Follow Up Required'),
        ('escalated', 'Escalated'),
        ('transferred', 'Transferred'),
        ('no_answer', 'No Answer'),
        ('voicemail', 'Voicemail'),
        ('wrong_number', 'Wrong Number'),
        ('spam', 'Spam'),
        ('other', 'Other'),
    ], string='Disposition')

    # Rating
    customer_rating = fields.Selection([
        ('1', '1 - Very Poor'),
        ('2', '2 - Poor'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Customer Rating')

    # Transfer info
    transferred_from = fields.Many2one(
        'cc.agent',
        string='Transferred From',
        ondelete='set null'
    )
    transferred_to = fields.Many2one(
        'cc.agent',
        string='Transferred To',
        ondelete='set null'
    )

    # Recording
    recording_url = fields.Char(string='Recording URL')
    has_recording = fields.Boolean(string='Has Recording', default=False)

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('cc.call') or 'New'
        return super().create(vals)

    @api.depends('start_time', 'answer_time', 'end_time')
    def _compute_durations(self):
        for record in self:
            record.wait_duration = 0
            record.talk_duration = 0
            record.total_duration = 0

            if record.start_time and record.answer_time:
                diff = record.answer_time - record.start_time
                record.wait_duration = int(diff.total_seconds())

            if record.answer_time and record.end_time:
                diff = record.end_time - record.answer_time
                record.talk_duration = int(diff.total_seconds())

            if record.start_time and record.end_time:
                diff = record.end_time - record.start_time
                record.total_duration = int(diff.total_seconds())

    def action_answer(self):
        """Answer the call"""
        self.write({
            'status': 'in_progress',
            'answer_time': fields.Datetime.now()
        })
        if self.agent_id:
            self.agent_id.action_set_busy()
            self.agent_id.last_call_time = fields.Datetime.now()

    def action_hold(self):
        """Put call on hold"""
        self.write({'status': 'on_hold'})

    def action_resume(self):
        """Resume call from hold"""
        self.write({'status': 'in_progress'})

    def action_complete(self):
        """Complete the call"""
        self.write({
            'status': 'completed',
            'end_time': fields.Datetime.now()
        })
        if self.agent_id:
            self.agent_id.action_set_after_call()
            self.agent_id.total_calls += 1

    def action_transfer(self, target_agent_id):
        """Transfer call to another agent"""
        self.write({
            'status': 'transferred',
            'transferred_from': self.agent_id.id,
            'transferred_to': target_agent_id,
        })
        # Create new call for target agent
        new_call = self.copy({
            'agent_id': target_agent_id,
            'transferred_from': self.agent_id.id,
            'status': 'ringing',
            'start_time': fields.Datetime.now(),
            'answer_time': False,
            'end_time': False,
        })
        return new_call

    def to_dict(self):
        """Convert to dictionary for API response"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'interaction_type': self.interaction_type,
            'channel': self.channel,
            'status': self.status,
            'agent_id': self.agent_id.id if self.agent_id else None,
            'agent_name': self.agent_id.name if self.agent_id else None,
            'queue_id': self.queue_id.id if self.queue_id else None,
            'queue_name': self.queue_id.name if self.queue_id else None,
            'caller_number': self.caller_number,
            'caller_name': self.caller_name,
            'shadow_profile_id': self.shadow_profile_id.id if self.shadow_profile_id else None,
            'partner_id': self.partner_id.id if self.partner_id else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'answer_time': self.answer_time.isoformat() if self.answer_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'wait_duration': self.wait_duration,
            'talk_duration': self.talk_duration,
            'total_duration': self.total_duration,
            'disposition': self.disposition,
            'customer_rating': self.customer_rating,
            'notes': self.notes,
        }
