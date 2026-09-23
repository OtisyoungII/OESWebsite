import json
import unittest
from unittest.mock import Mock, patch
from flask import Flask
from chat import init_chat
from chat.providers import ChatEvent
from chat.service import ChatService, SAFE_ERROR, fit_messages
from chat.worker_relay import RelayError
from chat.worker_protocol import (CONTEXT_BUDGET, CONTEXT_MESSAGE_ALLOWANCE,
                                  CONTEXT_OUTPUT_ALLOWANCE, context_cost)
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
        self.assertFalse(state.serious)
        self.assertFalse(continuity.recent_serious)

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

    def test_current_intent_exits_grounded_topic(self):
        history = [
            {'role': 'user', 'content': 'What security controls does OES use?'},
            {'role': 'assistant', 'content': ('OES authentication architecture, data retention '
                                             'practices, encryption controls, certifications.')},
        ]
        for message in ('hi', 'can you make an apple pie?'):
            with self.subTest(message=message):
                state, continuity = self.analyze(message, history)
                self.assertEqual(state.interaction_kind, 'conversation')
                self.assertFalse(state.serious)
                self.assertFalse(state.requires_oes_facts)
                self.assertFalse(continuity.recent_serious)

        state, _ = self.analyze('how much does a website cost with OES?', history)
        self.assertTrue(state.serious)
        self.assertTrue(state.requires_oes_facts)

        pricing_history = history + [
            {'role': 'user', 'content': 'how much does a website cost with OES?'},
            {'role': 'assistant', 'content': 'Published pricing is not in the approved facts.'},
        ]
        state, _ = self.analyze('lame', pricing_history)
        self.assertEqual(state.interaction_kind, 'conversation')
        self.assertFalse(state.serious)

    def test_explicit_referential_followup_may_inherit_immediate_user_topic(self):
        history = [{'role': 'user', 'content': 'What security controls does OES use?'},
                   {'role': 'assistant', 'content': 'Those details require confirmation.'}]
        state, continuity = self.analyze('what about that?', history)
        self.assertTrue(state.serious)
        self.assertTrue(continuity.recent_serious)

    def test_hypothetical_oes_design_is_reasoning_not_current_fact(self):
        state, _ = self.analyze('Could OES build a baseball scoring platform?')
        self.assertEqual(state.interaction_kind, 'hypothetical_oes_design')
        self.assertEqual(state.response_action, 'reason_hypothetically')
        self.assertEqual(state.grounding_mode, 'hypothetical_no_current_state_claims')
        self.assertFalse(state.requires_oes_facts)

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

    def test_fit_messages_drops_oldest_complete_exchanges(self):
        history = []
        for marker in ('oldest', 'middle', 'newest'):
            history.extend(({'role': 'user', 'content': marker + ' u' * 550},
                            {'role': 'assistant', 'content': marker + ' a' * 550}))
        messages = fit_messages('s' * 5000, history, 'current request')
        contents = [item['content'] for item in messages]
        self.assertNotIn(history[0]['content'], contents)
        self.assertNotIn(history[1]['content'], contents)
        self.assertEqual(messages[0], {'role': 'system', 'content': 's' * 5000})
        self.assertEqual(messages[-1], {'role': 'user', 'content': 'current request'})
        self.assertLessEqual(context_cost(messages), CONTEXT_BUDGET)

    def test_correction_instruction_is_refitted(self):
        provider = DraftProvider(["I'm just software.", "I call this look unforgettable."])
        history = [{'role': role, 'content': ('old context ' * 300)[:3000]}
                   for role in ('user', 'assistant')] * 5
        events = list(ChatService(provider).stream('why are u ugly?', history, {}))
        self.assertEqual([event.kind for event in events], ['start', 'delta', 'done'])
        self.assertEqual(len(provider.calls), 2)
        for call in provider.calls:
            self.assertLessEqual(context_cost(call), CONTEXT_BUDGET)
            self.assertEqual(call[-1], {'role': 'user', 'content': 'why are u ugly?'})
        self.assertIn('Regenerate once', provider.calls[1][0]['content'])

    def test_unicode_context_accounting_is_shared_with_worker(self):
        import worker.client
        messages = [{'role': 'system', 'content': 'policy 🧿'},
                    {'role': 'user', 'content': 'hello café'}]
        expected = (CONTEXT_OUTPUT_ALLOWANCE + 2 * CONTEXT_MESSAGE_ALLOWANCE
                    + sum(len(item['content'].encode('utf-8')) for item in messages))
        self.assertEqual(context_cost(messages), expected)
        self.assertIs(worker.client.context_cost, context_cost)

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

    def test_two_safe_style_misses_return_safe_draft(self):
        provider = DraftProvider(["I'm just software."] * 3)
        events = list(ChatService(provider).stream('why are u ugly?', [], {}))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual([e.kind for e in events], ['start','delta','done'])
        self.assertEqual(events[1].data['text'], "I'm just software.")

    def test_first_safe_draft_survives_unavailable_correction(self):
        class CorrectionUnavailable:
            def __init__(self): self.calls = 0
            def stream(self, messages):
                self.calls += 1
                if self.calls == 2:
                    raise RelayError('Worker unavailable', 'worker_unavailable_busy')
                return iter([ChatEvent('delta', {'text': 'How can I help?'}), ChatEvent('done', {})])
        provider = CorrectionUnavailable()
        events = list(ChatService(provider).stream('you again?', [], {}))
        self.assertEqual(provider.calls, 2)
        self.assertEqual([event.kind for event in events], ['start', 'delta', 'done'])
        self.assertEqual(events[1].data['text'], 'How can I help?')

    def test_hard_character_failure_remains_blocked(self):
        provider = DraftProvider(['OES is SOC 2 certified.'] * 2)
        events = list(ChatService(provider).stream('you again?', [], {}))
        self.assertEqual([event.kind for event in events], ['start', 'error'])
        self.assertEqual(events[-1].data['message'], SAFE_ERROR)

    def test_ordinary_conversation_skips_character_safety_review(self):
        for message in ('hi', 'making it one day at a time'):
            with self.subTest(message=message), \
                 patch('chat.service.validate_character_safety', side_effect=AssertionError('character path')):
                events = list(ChatService(DraftProvider(['Hello there.'])).stream(message, [], {}))
                self.assertEqual([event.kind for event in events], ['start', 'delta', 'done'])

    def test_character_style_failure_never_becomes_safe_error(self):
        provider = DraftProvider(['How can I help you?', 'What can I do for you?'])
        events = list(ChatService(provider).stream('great we got you working again', [], {}))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual([event.kind for event in events], ['start', 'delta', 'done'])

    def test_safe_error_has_one_content_free_failure_log(self):
        marker_message = 'you again private-message-marker'
        marker_response = 'OES is certified private-response-marker.'
        with patch('chat.service.LOG') as logger:
            events = list(ChatService(DraftProvider([marker_response] * 2)).stream(
                marker_message, [], {}))
        self.assertEqual([event.kind for event in events], ['start', 'error'])
        failures = [call for call in logger.warning.call_args_list
                    if call.args and call.args[0].startswith('chat request failed')]
        self.assertEqual(len(failures), 1)
        log_text = str(logger.mock_calls)
        self.assertIn('response_validation_exhausted', log_text)
        self.assertNotIn(marker_message, log_text)
        self.assertNotIn(marker_response, log_text)

    def test_genuine_service_failures_log_specific_category_once(self):
        cases = [
            ('provider_event_protocol', DraftProvider([None])),
            ('incomplete_provider_stream', type('Incomplete', (), {
                'stream': lambda self, messages: iter([ChatEvent('delta', {'text': 'partial'})])})()),
            ('response_output_limit', DraftProvider(['x' * 16001])),
        ]
        for expected, provider in cases:
            with self.subTest(category=expected), patch('chat.service.LOG') as logger:
                events = list(ChatService(provider).stream('ordinary statement', [], {}))
                self.assertEqual(events[0].kind, 'start')
                self.assertEqual(events[-1].kind, 'error')
                failures = [call for call in logger.warning.call_args_list
                            if call.args and call.args[0].startswith('chat request failed')]
                self.assertEqual(len(failures), 1)
                self.assertIn(expected, str(failures[0]))

        provider = DraftProvider(['{"fact_ids":["company_overview"]}'])
        with patch('chat.service.LOG') as logger, \
             patch('chat.service.render_public_fact_selection', side_effect=RuntimeError('private')):
            events = list(ChatService(provider).stream('Tell me about OES', [], {}))
        self.assertEqual([event.kind for event in events], ['start', 'error'])
        failures = [call for call in logger.warning.call_args_list
                    if call.args and call.args[0].startswith('chat request failed')]
        self.assertEqual(len(failures), 1)
        self.assertIn('grounded_rendering', str(failures[0]))

    def test_request_attempt_correlation_is_content_free(self):
        class TracedProvider(DraftProvider):
            def __init__(self, drafts):
                super().__init__(drafts); self.traces = []
            def set_trace(self, request_id, attempt):
                self.traces.append((request_id, attempt))
        provider = TracedProvider(['How can I help?', "I'm still here."])
        with patch('chat.service.LOG') as logger:
            events = list(ChatService(provider).stream('you again correlation-input', [], {}))
        self.assertEqual([event.kind for event in events], ['start', 'delta', 'done'])
        request_id = events[0].data['request_id']
        self.assertEqual(provider.traces, [(request_id, 1), (request_id, 2)])
        self.assertIn(request_id, str(logger.mock_calls))
        self.assertNotIn('correlation-input', str(logger.mock_calls))
        self.assertNotIn('How can I help?', str(logger.mock_calls))

    def test_user_identity_is_conversation_not_oes_fact(self):
        for message in ('my name is Otis', "I'm Otis", 'call me Otis'):
            with self.subTest(message=message):
                state, _ = self.analyze(message)
                self.assertEqual(state.interaction_kind, 'conversation')
                self.assertFalse(state.requires_oes_facts)
        for message in ('Tell me about Otis Execution Systems', 'Tell me about OES'):
            with self.subTest(message=message):
                state, _ = self.analyze(message)
                self.assertEqual(state.interaction_kind, 'oes_question')
                self.assertTrue(state.requires_oes_facts)

        provider = DraftProvider(['Nice to meet you.'])
        list(ChatService(provider).stream('my name is Otis', [], {}))
        self.assertNotIn('Select up to four relevant approved fact IDs',
                         provider.calls[0][0]['content'])

    def test_serious_path_does_not_retry(self):
        provider = DraftProvider(['OES has SOC 2'])
        events = list(ChatService(provider).stream('why are u ugly? security', [], {}))
        self.assertEqual(len(provider.calls), 1)
        text = ''.join(e.data.get('text','') for e in events)
        self.assertIn('security controls', text)
        self.assertIn('not listed', text)
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
