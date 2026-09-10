from dataclasses import asdict
from pathlib import Path
import unittest
from unittest.mock import Mock
from flask import Flask
from chat import init_chat
from chat.observations import (ObservationState, InferenceState, infer, observation_contract,
                               InitiationRestraint, decide_initiation, validate_context)
from chat.situation import SituationAnalyzer


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.observed = ObservationState(section='products', project='chaseingreen',
                                         time_on_section_seconds=46, details_opened_count=2)
        self.app = Flask(__name__)
        init_chat(self.app)
        self.client = self.app.test_client()

    def decision(self, restraint=None, observed=None):
        return decide_initiation(observed or self.observed, restraint or InitiationRestraint())

    def test_separate_models(self):
        interpretation = infer(self.observed)
        self.assertIsInstance(interpretation, InferenceState)
        self.assertNotIn('possible_interest', asdict(self.observed))
        self.assertEqual(interpretation.needs_guidance, 'unknown')
        self.assertIn('details_opened_count=2', interpretation.source_observations)

    def test_browser_cannot_control_inference_or_policy(self):
        for key in ['inferred_interest','possible_interest','identity','emotion','SituationState',
                    'response_action','certainty','humor_allowed','serious','grounding_mode']:
            payload = {'message':'hello','context':{key:True}}
            self.assertEqual(self.client.post('/api/chat',json=payload).status_code,400)
            self.assertEqual(self.client.post('/api/chat/initiation',json={'context':{key:True}}).status_code,400)

    def test_numeric_clamps(self):
        data = validate_context({'time_on_section_seconds':10**1000, 'details_opened_count':-2,
                                 'chat_open_count':25.5, 'chat_message_count':500})
        self.assertEqual(data, {'time_on_section_seconds':3600,'details_opened_count':0,
                                'chat_open_count':20,'chat_message_count':100})
        for value in [True, '42', None, [], float('inf'), float('nan')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_context({'time_on_section_seconds':value})

    def test_weak_signals_silent(self):
        for observation in [ObservationState(time_on_section_seconds=20),
                            ObservationState(section='products',time_on_section_seconds=3600),
                            ObservationState(section='products',project='chaseingreen'),
                            ObservationState(section='products',details_opened_count=10)]:
            self.assertEqual(self.decision(observed=observation).action,'stay_silent')

    def test_combined_signals_allow_help(self):
        self.assertEqual(self.decision().action,'offer_help')
        observation=ObservationState(section='products',project='chaseingreen',time_on_section_seconds=90)
        self.assertEqual(self.decision(observed=observation).action,'offer_help')

    def test_testflight_suppresses(self):
        observation=ObservationState(**(asdict(self.observed)|{'testflight_clicked':True}))
        self.assertEqual(self.decision(observed=observation).reason,'testflight_already_clicked')

    def test_dismissal_suppresses(self):
        self.assertEqual(self.decision(InitiationRestraint(dismissed=True)).reason,'dismissed')

    def test_visit_limit_cooldown_and_duplicate(self):
        for restraint, reason in [(InitiationRestraint(visit_offered=True),'visit_already_offered'),
                                  (InitiationRestraint(suggestion_seen=True),'suggestion_already_seen'),
                                  (InitiationRestraint(seconds_since_last=179),'cooldown')]:
            self.assertEqual(self.decision(restraint).reason,reason)
        self.assertEqual(self.decision(InitiationRestraint(seconds_since_last=180)).action,'offer_help')

    def test_user_chat_precedence(self):
        observation=ObservationState(**(asdict(self.observed)|{'chat_message_count':1}))
        self.assertEqual(self.decision(observed=observation).reason,'user_chat_precedence')
        self.assertEqual(self.decision(InitiationRestraint(user_active=True)).action,'stay_silent')

    def test_contract_is_explicitly_tentative(self):
        contract=observation_contract(self.observed,infer(self.observed))
        self.assertIn('Possible interpretation (tentative heuristic, not fact)',contract)
        self.assertIn('Never state the interpretation as fact',contract)
        self.assertNotIn('Visitor is interested in ChaseInGreen',contract)
        self.assertIn('not proof of reading or attention',contract)

    def test_confidence_bounds(self):
        for seconds in [0,20,46,90,3600]:
            result=infer(ObservationState(time_on_section_seconds=seconds))
            self.assertGreaterEqual(result.confidence,0)
            self.assertLessEqual(result.confidence,1)

    def test_serious_still_wins(self):
        state,_=SituationAnalyzer().analyze('why are u ugly? procurement security',[],asdict(self.observed))
        self.assertTrue(state.serious)
        self.assertFalse(state.humor_allowed)
        self.assertEqual(state.grounding_mode,'approved_fact_selection')

    def test_endpoint_does_not_call_provider(self):
        factory=Mock()
        self.app.extensions['chat_provider_factory']=factory
        payload={'context':{k:v for k,v in asdict(self.observed).items() if v is not None}}
        response=self.client.post('/api/chat/initiation',json=payload)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['action'],'offer_help')
        self.assertNotIn('Set-Cookie',response.headers)
        factory.assert_not_called()

    def test_endpoint_protocol_and_restraint_validation(self):
        self.assertEqual(self.client.get('/api/chat/initiation').status_code,405)
        self.assertEqual(self.client.post('/api/chat/initiation',data='bad').status_code,415)
        self.assertEqual(self.client.post('/api/chat/initiation',json={},headers={'Origin':'https://other.example'}).status_code,403)
        for restraint in [{'dismissed':'false'},{'seconds_since_last':True},{'serious':False}]:
            self.assertEqual(self.client.post('/api/chat/initiation',json={'restraint':restraint}).status_code,400)

    def test_debug_logging_allowlist(self):
        logger=Mock()
        self.app.logger=logger
        self.client.post('/api/chat/initiation',json={}).get_data()
        logger.info.assert_not_called()
        self.app.debug=True
        self.client.post('/api/chat/initiation',json={}).get_data()
        import json
        keys=[set(json.loads(call.args[1])) for call in logger.info.call_args_list]
        self.assertEqual(keys,[{'section','project','time_on_section','details_opened_count','testflight_clicked'},
                               {'possible_interest','confidence'},{'action','reason'}])

    def test_no_persistent_browser_storage(self):
        root=Path(__file__).resolve().parents[1]
        for name in ['eyeball-observations.js','eyeball-chat.js']:
            text=(root/'static/js'/name).read_text(encoding='utf-8')
            for forbidden in ['localStorage','sessionStorage','document.cookie','indexedDB','sendBeacon']:
                self.assertNotIn(forbidden,text)
