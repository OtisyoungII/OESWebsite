from dataclasses import asdict
import json
import unittest
from unittest.mock import Mock
from flask import Flask
from chat import init_chat
from chat.observations import ObservationState, InitiationRestraint
from chat.initiative import (authorize_intent, InitiationIntent, validate_invitation,
                            substantially_repeated, generate_invitation)
from chat.providers import ChatEvent

VALID = 'Want me to walk through ChaseInGreen with you?'


class WordingProvider:
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


class InitiativeTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        init_chat(self.app)
        self.client = self.app.test_client()
        self.provider = WordingProvider([VALID])
        self.factory = Mock(return_value=self.provider)
        self.app.extensions['chat_provider_factory'] = self.factory
        self.context = {'section':'products', 'project':'chaseingreen',
                        'time_on_section_seconds':46, 'product_interaction_count':2}
        self.intent, _ = authorize_intent(ObservationState.from_context(self.context), InitiationRestraint(), [])

    def post(self, **extra):
        return self.client.post('/api/chat/invitation', json={'context':self.context, **extra})

    def test_browser_cannot_force_intent(self):
        for key in ['action','intent','InitiationIntent','target','reason','allowed_public_facts','max_words','tone','certainty','provider','model']:
            self.assertEqual(self.post(**{key:'override'}).status_code,400)
            self.assertEqual(self.post(context={**self.context,key:'override'}).status_code,400)
        self.factory.assert_not_called()

    def test_typed_server_intent(self):
        self.assertIsInstance(self.intent, InitiationIntent)
        self.assertEqual(self.intent.action,'offer_help')
        self.assertEqual(self.intent.target,'chaseingreen')
        self.assertEqual(self.intent.max_words,18)
        self.assertIn('visitor wants to buy',self.intent.forbidden_inferences)
        self.assertEqual(len(self.intent.allowed_public_facts),1)

    def test_live_signals_without_details(self):
        self.assertNotIn('details_opened_count',self.context)
        response=self.post()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['text'],VALID)
        self.assertEqual(self.provider.closed,1)

    def test_single_selection_long_dwell(self):
        self.context.update(time_on_section_seconds=90,product_interaction_count=1)
        self.assertEqual(self.post().json['action'],'offer_help')

    def test_stay_silent_never_constructs_provider(self):
        self.context['time_on_section_seconds']=20
        self.assertEqual(self.post().json['action'],'stay_silent')
        self.factory.assert_not_called()

    def test_permission_precedes_generation(self):
        def factory():
            # Invalid/suppressed requests must return before this function runs.
            self.assertEqual(self.context['time_on_section_seconds'],46)
            return self.provider
        self.app.extensions['chat_provider_factory']=factory
        self.assertEqual(self.post().json['action'],'offer_help')
        system=self.provider.calls[0][0]['content']
        self.assertIn('already-authorized',system)
        self.assertIn('You cannot authorize actions',system)
        self.assertNotIn('Approved public OES facts:',system)

    def test_inference_claim_rejected(self):
        for text in ['You are interested in ChaseInGreen, want help?',
                     'I know you want ChaseInGreen, want help?',
                     'You clearly like ChaseInGreen, want help?',
                     'You seem hesitant about ChaseInGreen, want help?']:
            self.assertIn('inference_as_fact',validate_invitation(text,self.intent,[]))

    def test_optional_question_is_not_inference(self):
        self.assertEqual(validate_invitation('Would you like help with ChaseInGreen?',self.intent,[]),())
        self.assertIn('inference_as_fact',validate_invitation('Would you like help because you clearly love ChaseInGreen?',self.intent,[]))

    def test_length_rejected(self):
        text='Want me to explain ChaseInGreen ' + 'gently '*20 + '?'
        self.assertIn('length',validate_invitation(text,self.intent,[]))

    def test_disclaimer_rejected(self):
        self.assertIn('generic_disclaimer',validate_invitation('As an AI, can I explain ChaseInGreen?',self.intent,[]))

    def test_unsupported_claims_rejected(self):
        for text in ['Want guaranteed profits with ChaseInGreen?',
                     "Want me to explain ChaseInGreen's integrations?",
                     'Want to explore ChaseInGreen, our IoT sensor platform?',
                     'ChaseInGreen has unlimited features, want help?']:
            self.assertIn('unsupported_product_claim',validate_invitation(text,self.intent,[]))

    def test_one_regeneration(self):
        self.provider.drafts=['You are interested in ChaseInGreen.',VALID]
        self.assertEqual(self.post().json['text'],VALID)
        self.assertEqual(len(self.provider.calls),2)
        self.assertEqual(self.provider.closed,2)

    def test_second_failure_silent(self):
        self.provider.drafts=['As an AI, can I explain ChaseInGreen?']*3
        response=self.post()
        self.assertEqual(response.json['action'],'stay_silent')
        self.assertNotIn('text',response.json)
        self.assertEqual(len(self.provider.calls),2)

    def test_dismissal_prevents_generation(self):
        self.assertEqual(self.post(restraint={'dismissed':True}).json['action'],'stay_silent')
        self.factory.assert_not_called()

    def test_prior_chat_prevents_generation(self):
        for key in ['chat_open_count','chat_message_count']:
            self.assertEqual(self.post(context={**self.context,key:1}).json['action'],'stay_silent')
        self.assertEqual(self.post(history=[{'role':'user','content':'hello'}]).json['action'],'stay_silent')
        self.factory.assert_not_called()

    def test_testflight_prevents_generation(self):
        self.context['testflight_clicked']=True
        self.assertEqual(self.post().json['action'],'stay_silent')
        self.factory.assert_not_called()

    def test_other_restraints_prevent_generation(self):
        for restraint in [{'visit_offered':True},{'suggestion_seen':True},{'seconds_since_last':179},{'user_active':True}]:
            self.assertEqual(self.post(restraint=restraint).json['action'],'stay_silent')
        self.factory.assert_not_called()

    def test_repeated_wording_suppressed(self):
        self.provider.drafts=[VALID,VALID]
        self.assertEqual(self.post(recent_invitations=[VALID]).json['action'],'stay_silent')
        self.assertTrue(substantially_repeated('Want me to walk through Lottovate with you?', [VALID]))
        self.assertIn('repetition',validate_invitation(VALID,self.intent,[VALID]))

    def test_serious_and_problem_context_silent(self):
        for message in ['security','legal','privacy','compliance','procurement','app is broken','urgent error']:
            response=self.post(history=[{'role':'user','content':message}])
            self.assertEqual(response.json['reason'],'serious_or_problem_context')
        self.assertEqual(self.post(context={**self.context,'section':'government'}).json['action'],'stay_silent')
        self.factory.assert_not_called()

    def test_uncertain_target_silent(self):
        self.context['section']='client-work'
        self.assertEqual(self.post().json['reason'],'uncertain_target')
        self.factory.assert_not_called()

    def test_provider_failure_silent(self):
        self.factory.side_effect=RuntimeError('private path')
        response=self.post()
        self.assertEqual(response.json['action'],'stay_silent')
        self.assertNotIn('private',response.get_data(as_text=True))

    def test_recent_text_bounds_and_protocol(self):
        for recent in ['not a list',[VALID]*4,['x'*241],[{}]]:
            self.assertEqual(self.post(recent_invitations=recent).status_code,400)
        self.assertEqual(self.client.get('/api/chat/invitation').status_code,405)
        self.assertEqual(self.client.post('/api/chat/invitation',data='bad').status_code,415)
        self.assertEqual(self.client.post('/api/chat/invitation',json={},headers={'Origin':'https://other.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/chat/invitation',data=' '*8193,content_type='application/json').status_code,413)
        self.factory.assert_not_called()

    def test_debug_logs_no_generated_text(self):
        logger=Mock()
        self.app.logger=logger
        self.post()
        logger.info.assert_not_called()
        self.app.debug=True
        self.provider.drafts=[VALID,VALID]
        self.post()
        fields=[set(json.loads(call.args[1])) for call in logger.info.call_args_list]
        self.assertEqual(fields,[{'action','target','reason'},{'attempt','status','validator_reason'}])
        self.assertNotIn(VALID,str(logger.mock_calls))
