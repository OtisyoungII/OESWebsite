"""Server-owned locale allowlist for the public Eyeball interface."""

DEFAULT_LOCALE = 'en'

LANGUAGE_INSTRUCTIONS = {
    'en': ('Respond in English unless the user clearly requests another language. '),
    'es': ('Respond in Spanish unless the user clearly requests another language. '),
    'fr': ('Respond in French unless the user clearly requests another language. '),
    'ar': ('Respond in Arabic unless the user clearly requests another language. '),
    'zh-CN': ('Respond in Simplified Chinese unless the user clearly requests another language. '),
}

DETERMINISTIC_RESPONSES = {
    'clarification_candidates': {
        'en': "I've got a few candidates. Did you mean…",
        'es': 'Tengo algunas opciones. ¿Quisiste decir…?',
        'fr': 'J’ai quelques possibilités. Vouliez-vous dire…',
        'ar': 'لديّ بعض الاحتمالات. هل تقصد…',
        'zh-CN': '我有几个可能的理解。你的意思是……',
    },
    'clarification_rephrase': {
        'en': "I couldn't determine that confidently. Try saying it another way.",
        'es': 'No pude determinarlo con seguridad. Intenta decirlo de otra manera.',
        'fr': 'Je n’ai pas pu le déterminer avec certitude. Essayez de le reformuler.',
        'ar': 'لم أتمكن من تحديد المقصود بثقة. حاول صياغته بطريقة أخرى.',
        'zh-CN': '我无法确定你的意思。请换一种说法。',
    },
    'unknown_visitor_reason': {
        'en': "I can't know why you're here. What caught your eye?",
        'es': 'No puedo saber por qué estás aquí. ¿Qué te llamó la atención?',
        'fr': 'Je ne peux pas savoir pourquoi vous êtes ici. Qu’est-ce qui a attiré votre attention ?',
        'ar': 'لا يمكنني معرفة سبب وجودك هنا. ما الذي لفت انتباهك؟',
        'zh-CN': '我无法知道你为什么来到这里。什么吸引了你的注意？',
    },
    'request_location': {
        'en': 'I need a location you explicitly provide before I can search nearby places.',
        'es': 'Necesito una ubicación que proporciones explícitamente antes de buscar lugares cercanos.',
        'fr': 'J’ai besoin d’un lieu que vous indiquez explicitement avant de rechercher des endroits à proximité.',
        'ar': 'أحتاج إلى موقع تقدمه صراحةً قبل أن أتمكن من البحث عن أماكن قريبة.',
        'zh-CN': '你需要明确提供一个位置，我才能搜索附近的地点。',
    },
    'lookup_limitation': {
        'en': "I couldn't verify the current part right now, so I won't guess.",
        'es': 'No pude verificar ahora la parte que requiere información actual, así que no voy a adivinar.',
        'fr': 'Je n’ai pas pu vérifier la partie actuelle pour le moment, donc je ne vais pas la deviner.',
        'ar': 'لم أتمكن من التحقق من الجزء الحالي الآن، لذلك لن أخمّن.',
        'zh-CN': '我目前无法核实需要最新信息的部分，因此不会猜测。',
    },
}


def validate_locale(value):
    """Accept only exact public locale identifiers; missing means English."""
    if value is None:
        return DEFAULT_LOCALE
    if not isinstance(value, str) or value not in LANGUAGE_INSTRUCTIONS:
        raise ValueError('Locale must be one of: en, es, fr, ar, zh-CN.')
    return value


def response_language_instruction(locale):
    """Return fixed policy text; browser values never become instruction prose."""
    return LANGUAGE_INSTRUCTIONS[locale]


def deterministic_response(key, locale):
    """Render reviewed fixed responses without involving untrusted text."""
    return DETERMINISTIC_RESPONSES[key][locale]
