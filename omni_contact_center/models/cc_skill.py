from odoo import models, fields, api


class CCSkill(models.Model):
    _name = 'cc.skill'
    _description = 'Contact Center Skill'
    _order = 'name'

    name = fields.Char(string='Skill Name', required=True, index=True)
    code = fields.Char(string='Code', index=True)
    description = fields.Text(string='Description')

    skill_type = fields.Selection([
        ('language', 'Language'),
        ('product', 'Product Knowledge'),
        ('technical', 'Technical'),
        ('soft', 'Soft Skill'),
        ('channel', 'Channel'),
        ('other', 'Other'),
    ], string='Skill Type', default='other', required=True)

    active = fields.Boolean(string='Active', default=True)

    # Relations
    agent_ids = fields.Many2many(
        'cc.agent',
        'cc_agent_skill_rel',
        'skill_id',
        'agent_id',
        string='Agents'
    )
    agent_count = fields.Integer(
        string='Agents Count',
        compute='_compute_agent_count'
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Skill code must be unique!'),
    ]

    @api.depends('agent_ids')
    def _compute_agent_count(self):
        for record in self:
            record.agent_count = len(record.agent_ids)

    def to_dict(self):
        """Convert to dictionary for API response"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'skill_type': self.skill_type,
            'description': self.description,
            'agent_count': self.agent_count,
        }
