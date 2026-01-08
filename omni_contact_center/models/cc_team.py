from odoo import models, fields, api


class CCTeam(models.Model):
    _name = 'cc.team'
    _description = 'Contact Center Team'
    _order = 'name'

    name = fields.Char(string='Team Name', required=True, index=True)
    code = fields.Char(string='Code', index=True)
    description = fields.Text(string='Description')

    active = fields.Boolean(string='Active', default=True)

    # Team Lead
    leader_id = fields.Many2one(
        'cc.agent',
        string='Team Leader',
        ondelete='set null',
        domain="[('team_id', '=', id)]"
    )

    # Relations
    agent_ids = fields.One2many(
        'cc.agent',
        'team_id',
        string='Agents'
    )
    agent_count = fields.Integer(
        string='Agents Count',
        compute='_compute_agent_count'
    )

    queue_ids = fields.Many2many(
        'cc.queue',
        'cc_team_queue_rel',
        'team_id',
        'queue_id',
        string='Assigned Queues'
    )

    # Statistics
    available_agent_count = fields.Integer(
        string='Available Agents',
        compute='_compute_available_agents'
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Team code must be unique!'),
    ]

    @api.depends('agent_ids')
    def _compute_agent_count(self):
        for record in self:
            record.agent_count = len(record.agent_ids)

    @api.depends('agent_ids', 'agent_ids.status')
    def _compute_available_agents(self):
        for record in self:
            record.available_agent_count = len(
                record.agent_ids.filtered(lambda a: a.status == 'available')
            )

    def to_dict(self):
        """Convert to dictionary for API response"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'leader_id': self.leader_id.id if self.leader_id else None,
            'leader_name': self.leader_id.name if self.leader_id else None,
            'agent_count': self.agent_count,
            'available_agent_count': self.available_agent_count,
            'queue_ids': self.queue_ids.ids,
        }
