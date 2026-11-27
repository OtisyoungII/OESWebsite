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
    'company_followup_limitation': {
        'en': "I can't verify that from OES's approved public information.",
        'es': 'No puedo verificarlo con la información pública aprobada de OES.',
        'fr': 'Je ne peux pas le vérifier à partir des informations publiques approuvées d’OES.',
        'ar': 'لا أستطيع التحقق من ذلك من المعلومات العامة المعتمدة لدى OES.',
        'zh-CN': '我无法根据 OES 批准公开的信息核实这一点。',
    },
    'company_followup_clarify': {
        'en': 'Which company or product do you mean?',
        'es': '¿A qué empresa o producto te refieres?',
        'fr': 'De quelle entreprise ou de quel produit parlez-vous ?',
        'ar': 'ما الشركة أو المنتج الذي تقصده؟',
        'zh-CN': '你指的是哪家公司或哪款产品？',
    },
    'company_business_guidance': {
        'en': "That can be a difficult situation. I can't verify OES's internal circumstances. If you need traction sooner, start with one customer group, test a paid pilot, and use the results to decide what to invest in next.",
        'es': 'Puede ser una situación difícil. No puedo verificar las circunstancias internas de OES. Si necesitas conseguir clientes pronto, elige un segmento, prueba un piloto de pago y decide dónde invertir según los resultados.',
        'fr': 'La situation peut être difficile. Je ne peux pas vérifier la situation interne d’OES. Si vous devez attirer des clients rapidement, choisissez un segment, testez un pilote payant et décidez où investir selon les résultats.',
        'ar': 'قد يكون هذا موقفًا صعبًا. لا يمكنني التحقق من ظروف OES الداخلية. إذا كنت بحاجة إلى جذب العملاء بسرعة، فاختر فئة واحدة وجرّب مشروعًا تجريبيًا مدفوعًا واستند إلى نتائجه لتحديد استثمارك التالي.',
        'zh-CN': '这可能是个难题。我无法核实 OES 的内部情况。如果需要更快吸引客户，可以先选择一个客户群体，测试付费试点，再根据结果决定下一步投入。',
    },
    'company_design_guidance': {
        'en': "I can't confirm what OES would build or deliver. To explore the idea, identify who would use it, choose one workflow for a prototype, and test it with those users before committing to a release.",
        'es': 'No puedo confirmar qué desarrollaría o entregaría OES. Para explorar la idea, identifica a los usuarios, elige un flujo para el prototipo y pruébalo antes de comprometerte con un lanzamiento.',
        'fr': 'Je ne peux pas confirmer ce qu’OES développerait ou livrerait. Pour explorer l’idée, identifiez les utilisateurs, choisissez un parcours à prototyper et testez-le avant de vous engager sur une sortie.',
        'ar': 'لا يمكنني تأكيد ما قد تطوره أو تسلمه OES. لاستكشاف الفكرة، حدد المستخدمين واختر سير عمل واحدًا لنموذج أولي واختبره معهم قبل الالتزام بالإطلاق.',
        'zh-CN': '我无法确认 OES 会开发或交付什么。要探索这个想法，可以先确定目标用户，选择一个工作流程制作原型，并在承诺上线之前与用户一起测试。',
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
