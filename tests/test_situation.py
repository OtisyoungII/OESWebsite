import json
import unittest
from unittest.mock import Mock
from flask import Flask
from chat import init_chat
from chat.providers import ChatEvent
from chat.service import ChatService
from chat.situation import (SituationAnalyzer, validate_playful, validate_character,
                            response_contract, character_style_instruction)


class DraftProvider:
    def __init__(self, drafts):
        self.drafts = drafts
        self.calls = []
        self.closed = 0

    def stream(self, messages):
        self.calls.append(messages)
        try:
            yield ChatEvent('delta', {'text': self.drafts[len(self.calls)-1]})
            yield ChatEvent('done', {})
        finally:
            self.closed += 1


class SituationTests(unittest.TestCase):
    def analyze(self, message='why are u ugly?', history=None, context=None):
        return SituationAnalyzer().analyze(message, history or [], context or {})

    def test_teasing_state(self):
        state, _ = self.analyze()
        self.assertEqual(state.interaction_kind, 'teasing')
        self.assertEqual(state.tone, 'playful')
        self.assertTrue(state.humor_allowed)
        self.assertFalse(state.serious)
        self.assertFalse(state.requires_oes_facts)
        self.assertFalse(state.identity_explanation_allowed)
        self.assertEqual(state.response_length, 'one_short_sentence')
        self.assertEqual(state.grounding_mode, 'character_no_new_facts')

    def test_serious_override(self):
        for term in ['security', 'procurement', 'legal', 'privacy', 'compliance', 'pricing', 'NDA', 'liability']:
            with self.subTest(term=term):
                state, _ = self.analyze('why are u ugly? ' + term)
                self.assertTrue(state.serious)
                self.assertFalse(state.humor_allowed)
                self.assertEqual(state.grounding_mode, 'approved_fact_selection')
        state, _ = self.analyze(context={'section':'government'})
        self.assertTrue(state.serious)

    def test_continuity(self):
        history = [{'role':'user','content':'why are u ugly?'},
                   {'role':'assistant','content':"I call this look unforgettable."}]
        state, continuity = self.analyze('another one', history)
        self.assertEqual(state.tone, 'playful')
        self.assertEqual(state.certainty, 'medium')
        self.assertEqual(continuity.current_tone, 'playful')
        self.assertTrue(continuity.recent_playful)
        self.assertEqual(continuity.recent_assistant_phrasing, (history[-1]['content'],))
        state, continuity = self.analyze(history=history+[{'role':'user','content':'security'}])
        self.assertTrue(state.serious)
        self.assertTrue(continuity.recent_serious)

    def test_character_directed_turn_continues_into_short_followup(self):
        history = [{'role': 'user', 'content': "you're back"},
                   {'role': 'assistant', 'content': 'Finally.'}]
        state, continuity = self.analyze('unfortunately', history)
        self.assertEqual(state.interaction_kind, 'character_followup')
        self.assertEqual(state.response_action, 'character_reply')
        self.assertTrue(continuity.recent_playful)

    def test_history_is_bounded_and_request_local(self):
        history = [{'role':'user','content':'security'}] + [{'role':'user','content':'hello'}]*10
        state, _ = self.analyze(history=history)
        self.assertFalse(state.serious)
        self.analyze(history=[{'role':'user','content':'security'}])
        self.assertFalse(self.analyze()[0].serious)

    def test_response_action_and_certainty(self):
        for message, action, certainty in [
            ('why are u ugly?', 'playful_reply', 'high'),
            ('Are you an AI?', 'explain_identity', 'high'),
            ('What does ChaseInGreen do?', 'answer', 'high'),
            ('security', 'grounded_answer', 'high'),
            ('you again?', 'character_reply', 'medium'),
            ('?', 'clarify', 'low'), ('hello', 'answer', 'medium')]:
            state, continuity = self.analyze(message)
            self.assertEqual(state.response_action, action)
            self.assertEqual(state.certainty, certainty)
            self.assertIn('action='+action, response_contract(state, continuity))

    def test_validator(self):
        _, continuity = self.analyze()
        for text, reason in [
            ("I'm just software.", 'identity_explanation'),
            ('I am sorry; how can I assist you?', 'generic_explanation'),
            ('Looks are overrated.', 'first_person'),
            ('I look fine. My taste is excellent.', 'one_sentence'),
            ('I ' + 'look '*40, 'length')]:
            self.assertIn(reason, validate_playful(text, continuity))
        self.assertEqual(validate_playful("I call this look unforgettable.", continuity), ())

    def test_character_banter_contract_and_validator(self):
        state, continuity = self.analyze('you again?')
        self.assertEqual(state.interaction_kind, 'character_banter')
        self.assertTrue(state.humor_allowed)
        self.assertEqual(state.grounding_mode, 'character_no_new_facts')
        self.assertIn('Do not reintroduce yourself', response_contract(state, continuity))
        for text, reason in [
            ("I'm OES Eyeball. What's on your mind?", 'self_introduction'),
            ('How can I assist you today?', 'customer_service'),
            ('I saw you clicking around the site.', 'visitor_narration'),
            ('I represent a trusted provider of secure solutions.', 'unsupported_claim'),
            ('ChaseInGreen is moving along nicely.', 'unsupported_claim'),
            ('Ready to chat?', 'customer_service'),
            ('I am a good chatbot, observing and learning.', 'identity_explanation'),
            ('My gaze is fixed on the page.', 'visitor_narration'),
            ("I'm just a collection of code and data.", 'identity_explanation'),
            ("I'm just a digital interface.", 'identity_explanation')]:
            self.assertIn(reason, validate_character(text, continuity))
        self.assertEqual(validate_character(
            "Unfortunately for everyone involved, I'm back.", continuity), ())

    def test_small_character_mode_hints_contain_no_canned_reply(self):
        cases = [('hey eyeball', 'greeting'), ('why trust you?', 'trust'),
                 ('what have you been doing?', 'playful activity'), ("you're back", 'presence')]
        for message, mode in cases:
            with self.subTest(message=message):
                hint = character_style_instruction(message)
                self.assertIn('Banter mode: ' + mode, hint)
                self.assertNotIn('Unfortunately for everyone involved', hint)

    def test_character_reply_regenerates_once(self):
        provider = DraftProvider(["I'm OES Eyeball. How can I assist you today?",
                                  "Unfortunately for everyone involved, I'm back."])
        events = list(ChatService(provider).stream("you're back", [], {}))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual([e.kind for e in events], ['start', 'delta', 'done'])
        self.assertNotIn('assist', ''.join(e.data.get('text', '') for e in events))
        self.assertIn('fresh reaction under 20 words',
                      provider.calls[-1][0]['content'])

    def test_oes_facts_take_precedence_over_character_banter(self):
        state, _ = self.analyze('what do you know about ChaseInGreen?')
        self.assertEqual(state.interaction_kind, 'oes_question')
        self.assertTrue(state.requires_oes_facts)

    def test_looking_question_is_character_banter_not_identity(self):
        state, _ = self.analyze('what are you looking at?')
        self.assertEqual(state.response_action, 'character_reply')

    def test_context_product_and_unknown_reason(self):
        state, _ = self.analyze('What can you tell me about this product?',
                                context={'section': 'products', 'project': 'chaseingreen'})
        self.assertTrue(state.requires_oes_facts)
        state, _ = self.analyze('Why am I looking at this?',
                                context={'section': 'products', 'project': 'lottovate'})
        self.assertEqual(state.interaction_kind, 'unknown_visitor_reason')
        self.assertEqual(state.grounding_mode, 'no_assumptions')

    def test_anti_repetition(self):
        _, continuity = self.analyze(history=[{'role':'assistant','content':"I may not be handsome, but I am memorable."}])
        for text in ["I may not be handsome, but I am memorable.",
                     "My look is memorable, but I am memorable.",
                     "I might not sparkle, but my charm travels."]:
            self.assertIn('repetition', validate_playful(text, continuity))

    def test_one_retry_then_valid(self):
        provider = DraftProvider(["I'm just software.", "I call this look unforgettable."])
        events = list(ChatService(provider).stream('why are u ugly?', [], {}))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.closed, 2)
        self.assertEqual([e.kind for e in events], ['start','delta','done'])
        self.assertNotIn('software', ''.join(e.data.get('text','') for e in events))
        self.assertIn('Regenerate once', provider.calls[-1][0]['content'])

    def test_retry_maximum_no_bad_draft_leak(self):
        provider = DraftProvider(["I'm just software."] * 3)
        events = list(ChatService(provider).stream('why are u ugly?', [], {}))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual([e.kind for e in events], ['start','error'])

    def test_serious_path_does_not_retry(self):
        provider = DraftProvider(['OES has SOC 2'])
        events = list(ChatService(provider).stream('why are u ugly? security', [], {}))
        self.assertEqual(len(provider.calls), 1)
        text = ''.join(e.data.get('text','') for e in events)
        self.assertIn('need to be confirmed', text)
        self.assertNotIn('SOC 2', text)

    def test_browser_cannot_set_state(self):
        app = Flask(__name__)
        init_chat(app)
        factory = Mock()
        app.extensions['chat_provider_factory'] = factory
        client = app.test_client()
        for key in ['SituationState','situation','tone','serious','humor_allowed','certainty','response_action']:
            for payload in [{'message':'hello',key:False}, {'message':'hello','context':{key:False}}]:
                self.assertEqual(client.post('/api/chat',json=payload).status_code,400)
        factory.assert_not_called()

    def test_debug_logs_only_allowed_fields(self):
        app = Flask(__name__)
        init_chat(app)
        app.extensions['chat_provider_factory'] = lambda: DraftProvider(['Hello'])
        client = app.test_client()
        logger = Mock()
        app.logger = logger
        secret = 'private message marker'
        client.post('/api/chat',json={'message':secret}).get_data()
        logger.info.assert_not_called()
        app.debug = True
        client.post('/api/chat',json={'message':secret}).get_data()
        fields = json.loads(logger.info.call_args.args[1])
        self.assertEqual(set(fields), {'interaction_kind','tone','serious','facts_required',
                                      'grounding_mode','response_action','certainty'})
        self.assertNotIn(secret, str(logger.mock_calls))
