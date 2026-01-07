import json
from odoo import http
from odoo.http import request, Response


class ShadowProfileAPI(http.Controller):
    """REST API for Shadow Profiles - Used by N8N"""

    def _json_response(self, data, status=200):
        """Return JSON response"""
        return Response(
            json.dumps(data, default=str),
            status=status,
            mimetype='application/json'
        )

    def _error_response(self, message, status=400):
        """Return error response"""
        return self._json_response({
            'success': False,
            'error': message
        }, status)

    def _success_response(self, data=None, message=None):
        """Return success response"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return self._json_response(response)

    # ============== SHADOW PROFILE ENDPOINTS ==============

    @http.route('/api/v1/shadow', type='http', auth='api_key', methods=['GET'], csrf=False)
    def list_shadows(self, **kwargs):
        """List all shadow profiles with optional filters"""
        try:
            domain = []

            # Filters
            if kwargs.get('status'):
                domain.append(('status', '=', kwargs['status']))
            if kwargs.get('channel'):
                domain.append(('source_channel', '=', kwargs['channel']))
            if kwargs.get('is_converted'):
                domain.append(('is_converted', '=', kwargs['is_converted'] == 'true'))

            # Pagination
            limit = int(kwargs.get('limit', 100))
            offset = int(kwargs.get('offset', 0))

            shadows = request.env['shadow.profile'].sudo().search(
                domain, limit=limit, offset=offset, order='last_contact_date desc'
            )
            total = request.env['shadow.profile'].sudo().search_count(domain)

            return self._success_response({
                'records': [s.to_dict() for s in shadows],
                'total': total,
                'limit': limit,
                'offset': offset
            })
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/shadow/<int:shadow_id>', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_shadow(self, shadow_id, **kwargs):
        """Get single shadow profile"""
        try:
            shadow = request.env['shadow.profile'].sudo().browse(shadow_id)
            if not shadow.exists():
                return self._error_response('Shadow profile not found', 404)
            return self._success_response(shadow.to_dict())
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/shadow', type='json', auth='api_key', methods=['POST'], csrf=False)
    def create_shadow(self, **kwargs):
        """Create new shadow profile"""
        try:
            data = request.jsonrequest
            required = ['name']
            for field in required:
                if not data.get(field):
                    return {'success': False, 'error': f'{field} is required'}

            shadow = request.env['shadow.profile'].sudo().create(data)
            return {'success': True, 'data': shadow.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/v1/shadow/<int:shadow_id>', type='json', auth='api_key', methods=['PUT'], csrf=False)
    def update_shadow(self, shadow_id, **kwargs):
        """Update shadow profile"""
        try:
            shadow = request.env['shadow.profile'].sudo().browse(shadow_id)
            if not shadow.exists():
                return {'success': False, 'error': 'Shadow profile not found'}

            data = request.jsonrequest
            shadow.write(data)
            return {'success': True, 'data': shadow.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/v1/shadow/<int:shadow_id>', type='http', auth='api_key', methods=['DELETE'], csrf=False)
    def delete_shadow(self, shadow_id, **kwargs):
        """Delete shadow profile"""
        try:
            shadow = request.env['shadow.profile'].sudo().browse(shadow_id)
            if not shadow.exists():
                return self._error_response('Shadow profile not found', 404)
            shadow.unlink()
            return self._success_response(message='Shadow profile deleted')
        except Exception as e:
            return self._error_response(str(e), 500)

    # ============== SEARCH ENDPOINTS ==============

    @http.route('/api/v1/shadow/search', type='http', auth='api_key', methods=['GET'], csrf=False)
    def search_shadow(self, **kwargs):
        """Search shadow by phone, social ID, or email"""
        try:
            Shadow = request.env['shadow.profile'].sudo()
            shadow = None

            if kwargs.get('phone'):
                shadow = Shadow.search([('phone', '=', kwargs['phone'])], limit=1)
            elif kwargs.get('whatsapp_id'):
                shadow = Shadow.search([('whatsapp_id', '=', kwargs['whatsapp_id'])], limit=1)
            elif kwargs.get('facebook_id'):
                shadow = Shadow.search([('facebook_id', '=', kwargs['facebook_id'])], limit=1)
            elif kwargs.get('instagram_id'):
                shadow = Shadow.search([('instagram_id', '=', kwargs['instagram_id'])], limit=1)
            elif kwargs.get('telegram_id'):
                shadow = Shadow.search([('telegram_id', '=', kwargs['telegram_id'])], limit=1)
            elif kwargs.get('email'):
                shadow = Shadow.search([('email', '=', kwargs['email'])], limit=1)
            elif kwargs.get('identifier'):
                shadow = Shadow.search_by_identifier(kwargs['identifier'])

            if shadow:
                return self._success_response(shadow.to_dict())
            return self._success_response(None)
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/shadow/find-or-create', type='json', auth='api_key', methods=['POST'], csrf=False)
    def find_or_create_shadow(self, **kwargs):
        """Find existing shadow or create new one"""
        try:
            data = request.jsonrequest
            platform = data.get('platform')
            platform_id = data.get('platform_id')
            name = data.get('name')

            if not platform or not platform_id:
                return {'success': False, 'error': 'platform and platform_id required'}

            shadow = request.env['shadow.profile'].sudo().find_or_create(
                platform, platform_id, name
            )
            if shadow:
                return {'success': True, 'data': shadow.to_dict()}
            return {'success': False, 'error': 'Invalid platform'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============== ACTION ENDPOINTS ==============

    @http.route('/api/v1/shadow/<int:shadow_id>/qualify', type='json', auth='api_key', methods=['POST'], csrf=False)
    def qualify_shadow(self, shadow_id, **kwargs):
        """Mark shadow as qualified"""
        try:
            shadow = request.env['shadow.profile'].sudo().browse(shadow_id)
            if not shadow.exists():
                return {'success': False, 'error': 'Shadow profile not found'}
            shadow.action_qualify()
            return {'success': True, 'data': shadow.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/v1/shadow/<int:shadow_id>/convert', type='json', auth='api_key', methods=['POST'], csrf=False)
    def convert_shadow(self, shadow_id, **kwargs):
        """Convert shadow to partner"""
        try:
            shadow = request.env['shadow.profile'].sudo().browse(shadow_id)
            if not shadow.exists():
                return {'success': False, 'error': 'Shadow profile not found'}
            partner = shadow.action_convert_to_partner()
            return {
                'success': True,
                'data': {
                    'shadow': shadow.to_dict(),
                    'partner_id': partner.id
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============== CONVERSATION ENDPOINTS ==============

    @http.route('/api/v1/shadow/<int:shadow_id>/conversations', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_conversations(self, shadow_id, **kwargs):
        """Get conversations for a shadow profile"""
        try:
            shadow = request.env['shadow.profile'].sudo().browse(shadow_id)
            if not shadow.exists():
                return self._error_response('Shadow profile not found', 404)

            conversations = [{
                'id': c.id,
                'channel': c.channel,
                'message': c.message,
                'direction': c.direction,
                'timestamp': c.timestamp.isoformat() if c.timestamp else None,
                'is_ai_response': c.is_ai_response,
            } for c in shadow.conversation_ids]

            return self._success_response(conversations)
        except Exception as e:
            return self._error_response(str(e), 500)

    @http.route('/api/v1/conversation', type='json', auth='api_key', methods=['POST'], csrf=False)
    def add_conversation(self, **kwargs):
        """Add conversation message"""
        try:
            data = request.jsonrequest
            required = ['shadow_profile_id', 'channel', 'message', 'direction']
            for field in required:
                if not data.get(field):
                    return {'success': False, 'error': f'{field} is required'}

            conversation = request.env['shadow.conversation'].sudo().create(data)

            # Update message count
            shadow = conversation.shadow_profile_id
            shadow.sudo().write({
                'message_count': shadow.message_count + 1,
                'last_contact_date': conversation.timestamp
            })

            return {
                'success': True,
                'data': {
                    'id': conversation.id,
                    'shadow_id': shadow.id,
                    'message_count': shadow.message_count
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ============== STATS ENDPOINT ==============

    @http.route('/api/v1/shadow/stats', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_stats(self, **kwargs):
        """Get shadow profile statistics"""
        try:
            Shadow = request.env['shadow.profile'].sudo()

            stats = {
                'total': Shadow.search_count([]),
                'anonymous': Shadow.search_count([('status', '=', 'anonymous')]),
                'qualified': Shadow.search_count([('status', '=', 'qualified')]),
                'pending_registration': Shadow.search_count([('status', '=', 'pending_registration')]),
                'registered': Shadow.search_count([('status', '=', 'registered')]),
                'converted': Shadow.search_count([('is_converted', '=', True)]),
                'by_channel': {
                    'whatsapp': Shadow.search_count([('source_channel', '=', 'whatsapp')]),
                    'facebook': Shadow.search_count([('source_channel', '=', 'facebook')]),
                    'instagram': Shadow.search_count([('source_channel', '=', 'instagram')]),
                    'telegram': Shadow.search_count([('source_channel', '=', 'telegram')]),
                    'phone': Shadow.search_count([('source_channel', '=', 'phone')]),
                    'website': Shadow.search_count([('source_channel', '=', 'website')]),
                }
            }
            return self._success_response(stats)
        except Exception as e:
            return self._error_response(str(e), 500)
