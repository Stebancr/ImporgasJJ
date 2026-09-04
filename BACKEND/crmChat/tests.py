from unittest.mock import Mock, patch

from django.urls import reverse
from rest_framework.test import APITestCase

from .models import ChatSession
from .ollama_service import ollama_service


class ConversationStateTests(APITestCase):
    def test_purchase_budget_topic_change_and_return(self):
        state = ollama_service.update_state('Quiero comprar un calentador')
        self.assertEqual(state['intent'], 'purchase')
        self.assertEqual(state['product'], 'calentador')
        self.assertFalse(state['needs_human'])

        state = ollama_service.update_state('Tengo un millón', state)
        self.assertEqual(state['budget'], 1_000_000)
        self.assertEqual(state['stage'], 'recommendation')

        state = ollama_service.update_state('¿Y hacen envíos?', state)
        self.assertEqual(state['topic'], 'shipping')
        self.assertEqual(state['product'], 'calentador')
        self.assertEqual(state['budget'], 1_000_000)

        state = ollama_service.update_state('¿Qué garantía manejan?', state)
        self.assertEqual(state['topic'], 'warranty')
        self.assertEqual(state['product'], 'calentador')
        state = ollama_service.update_state('¿Y cuál calentador me recomiendas?', state)
        self.assertEqual(state['topic'], 'product')
        self.assertIn('warranty', state['previous_topics'])

    def test_buying_does_not_escalate_but_explicit_advisor_does(self):
        self.assertFalse(ollama_service.needs_human_agent('Quiero comprar un celular'))
        self.assertTrue(ollama_service.needs_human_agent('Quiero hablar con un asesor'))
        self.assertTrue(ollama_service.needs_human_agent('No me estás entendiendo'))

    @patch('crmChat.ollama_service.requests.post')
    def test_api_persists_structured_memory_across_turns(self, ollama_post):
        provider_response = Mock()
        provider_response.raise_for_status.return_value = None
        provider_response.json.return_value = {'message': {'content': 'Respuesta basada en el contexto.'}}
        ollama_post.return_value = provider_response

        session_id = None
        responses = {}
        for message in ('Hola', 'Quiero comprar un celular', 'Tengo un millón', '¿Cuál me recomiendas?', '¿Y hacen envíos?'):
            response = self.client.post(reverse('bot-chat'), {
                'message': message,
                'session_id': session_id,
                'user_name': 'Cliente',
            }, format='json')
            self.assertEqual(response.status_code, 200)
            session_id = response.data['session_id']
            responses[message] = response.data['message']

        session = ChatSession.objects.get(pk=session_id)
        self.assertEqual(session.conversation_state['intent'], 'purchase')
        self.assertEqual(session.conversation_state['product'], 'celular')
        self.assertEqual(session.conversation_state['budget'], 1_000_000)
        self.assertEqual(session.conversation_state['topic'], 'shipping')
        self.assertIn('No encuentro celular', responses['¿Cuál me recomiendas?'])
        self.assertIn('envíos nacionales', responses['¿Y hacen envíos?'])
        self.assertLessEqual(len(ollama_post.call_args.kwargs['json']['messages']), 12)

        response = self.client.post(reverse('bot-chat'), {
            'message': 'Quiero hablar con un asesor',
            'session_id': session_id,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['needs_login'])
        session.refresh_from_db()
        self.assertTrue(session.conversation_state['needs_human'])
