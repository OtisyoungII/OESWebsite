export const EYEBALL_LOCALE_STORAGE_KEY = 'oes.eyeball.locale';
export const DEFAULT_EYEBALL_LOCALE = 'en';

export const EYEBALL_LOCALES = Object.freeze({
    en: Object.freeze({
        name: 'English', tag: 'en', dir: 'ltr', strings: Object.freeze({
            languageLabel: 'Eyeball language', title: 'OES EYEBALL', subtitle: 'INTELLIGENCE INTERFACE',
            close: 'Close', closeLabel: 'Close Eyeball Chat', coreOnline: 'CORE ONLINE', publicAccess: 'PUBLIC ACCESS',
            notice: 'Public AI assistant. Confirm important details with OES. Do not share private information.',
            disclosure: 'Eyeball uses multilingual model capabilities; interface text is localized separately. Automated language output can contain errors.',
            conversationLabel: 'Eyeball conversation', greeting: 'What are you trying to accomplish?',
            messageLabel: 'Your message', placeholder: 'Describe your objective…',
            inputHelp: 'Enter to send · Shift+Enter for a new line · 4,000 characters maximum',
            ready: 'Ready', responding: 'Eyeball is responding…', stopped: 'Response stopped.',
            interrupted: 'Response interrupted. You can try again.', stop: 'Stop', send: 'Send',
            you: 'YOU', eyeball: 'EYEBALL', safeError: 'Eyeball is temporarily unavailable. Please try again shortly.',
            invitation: 'Questions about this product? Ask Eyeball.', invitationLabel: 'Optional Eyeball invitation',
            dismissInvitation: 'Dismiss Eyeball invitation for this page visit',
            clarificationLabel: 'Eyeball clarification choices', clarificationSomethingElse: 'Something else'
        })
    }),
    es: Object.freeze({
        name: 'Español', tag: 'es', dir: 'ltr', strings: Object.freeze({
            languageLabel: 'Idioma de Eyeball', title: 'OES EYEBALL', subtitle: 'INTERFAZ DE INTELIGENCIA',
            close: 'Cerrar', closeLabel: 'Cerrar el chat de Eyeball', coreOnline: 'CORE EN LÍNEA', publicAccess: 'ACCESO PÚBLICO',
            notice: 'Asistente público de IA. Confirma los detalles importantes con OES. No compartas información privada.',
            disclosure: 'Eyeball usa capacidades de modelo multilingüe; el texto de la interfaz se localiza por separado. El lenguaje automatizado puede contener errores.',
            conversationLabel: 'Conversación con Eyeball', greeting: '¿Qué intentas lograr?', messageLabel: 'Tu mensaje',
            placeholder: 'Describe tu objetivo…', inputHelp: 'Intro para enviar · Mayús+Intro para una línea nueva · máximo de 4.000 caracteres',
            ready: 'Listo', responding: 'Eyeball está respondiendo…', stopped: 'Respuesta detenida.',
            interrupted: 'La respuesta se interrumpió. Puedes intentarlo de nuevo.', stop: 'Detener', send: 'Enviar',
            you: 'TÚ', eyeball: 'EYEBALL', safeError: 'Eyeball no está disponible temporalmente. Inténtalo de nuevo en breve.',
            invitation: '¿Tienes preguntas sobre este producto? Pregúntale a Eyeball.', invitationLabel: 'Invitación opcional de Eyeball',
            dismissInvitation: 'Descartar la invitación de Eyeball durante esta visita',
            clarificationLabel: 'Opciones de aclaración de Eyeball', clarificationSomethingElse: 'Otra cosa'
        })
    }),
    fr: Object.freeze({
        name: 'Français', tag: 'fr', dir: 'ltr', strings: Object.freeze({
            languageLabel: 'Langue d’Eyeball', title: 'OES EYEBALL', subtitle: 'INTERFACE D’INTELLIGENCE',
            close: 'Fermer', closeLabel: 'Fermer le chat Eyeball', coreOnline: 'CORE EN LIGNE', publicAccess: 'ACCÈS PUBLIC',
            notice: 'Assistant IA public. Confirmez les détails importants auprès d’OES. Ne partagez aucune information privée.',
            disclosure: 'Eyeball utilise les capacités multilingues du modèle ; le texte de l’interface est localisé séparément. Les réponses automatisées peuvent contenir des erreurs.',
            conversationLabel: 'Conversation avec Eyeball', greeting: 'Qu’essayez-vous d’accomplir ?', messageLabel: 'Votre message',
            placeholder: 'Décrivez votre objectif…', inputHelp: 'Entrée pour envoyer · Maj+Entrée pour une nouvelle ligne · 4 000 caractères maximum',
            ready: 'Prêt', responding: 'Eyeball répond…', stopped: 'Réponse arrêtée.',
            interrupted: 'La réponse a été interrompue. Vous pouvez réessayer.', stop: 'Arrêter', send: 'Envoyer',
            you: 'VOUS', eyeball: 'EYEBALL', safeError: 'Eyeball est temporairement indisponible. Veuillez réessayer bientôt.',
            invitation: 'Des questions sur ce produit ? Demandez à Eyeball.', invitationLabel: 'Invitation facultative d’Eyeball',
            dismissInvitation: 'Ignorer l’invitation d’Eyeball pour cette visite',
            clarificationLabel: 'Choix de clarification d’Eyeball', clarificationSomethingElse: 'Autre chose'
        })
    }),
    ar: Object.freeze({
        name: 'العربية', tag: 'ar', dir: 'rtl', strings: Object.freeze({
            languageLabel: 'لغة Eyeball', title: 'OES EYEBALL', subtitle: 'واجهة الذكاء',
            close: 'إغلاق', closeLabel: 'إغلاق محادثة Eyeball', coreOnline: 'CORE متصل', publicAccess: 'وصول عام',
            notice: 'مساعد ذكاء اصطناعي عام. أكّد التفاصيل المهمة مع OES. لا تشارك معلومات خاصة.',
            disclosure: 'يستخدم Eyeball قدرات النموذج متعددة اللغات، بينما تُوطّن نصوص الواجهة بشكل منفصل. قد تحتوي المخرجات الآلية على أخطاء.',
            conversationLabel: 'محادثة Eyeball', greeting: 'ما الذي تحاول إنجازه؟', messageLabel: 'رسالتك',
            placeholder: 'صِف هدفك…', inputHelp: 'Enter للإرسال · Shift+Enter لسطر جديد · الحد الأقصى ٤٬٠٠٠ حرف',
            ready: 'جاهز', responding: 'Eyeball يرد…', stopped: 'تم إيقاف الرد.',
            interrupted: 'انقطع الرد. يمكنك المحاولة مرة أخرى.', stop: 'إيقاف', send: 'إرسال',
            you: 'أنت', eyeball: 'EYEBALL', safeError: 'Eyeball غير متاح مؤقتًا. حاول مرة أخرى بعد قليل.',
            invitation: 'لديك أسئلة عن هذا المنتج؟ اسأل Eyeball.', invitationLabel: 'دعوة اختيارية من Eyeball',
            dismissInvitation: 'تجاهل دعوة Eyeball لهذه الزيارة',
            clarificationLabel: 'خيارات توضيح Eyeball', clarificationSomethingElse: 'شيء آخر'
        })
    }),
    'zh-CN': Object.freeze({
        name: '简体中文', tag: 'zh-CN', dir: 'ltr', strings: Object.freeze({
            languageLabel: 'Eyeball 语言', title: 'OES EYEBALL', subtitle: '智能界面',
            close: '关闭', closeLabel: '关闭 Eyeball 对话', coreOnline: 'CORE 在线', publicAccess: '公开访问',
            notice: '公共 AI 助手。重要信息请向 OES 确认。请勿分享隐私信息。',
            disclosure: 'Eyeball 使用模型的多语言能力；界面文字单独进行本地化。自动生成的语言可能包含错误。',
            conversationLabel: 'Eyeball 对话', greeting: '你想完成什么？', messageLabel: '你的消息',
            placeholder: '描述你的目标…', inputHelp: '按 Enter 发送 · Shift+Enter 换行 · 最多 4,000 个字符',
            ready: '就绪', responding: 'Eyeball 正在回复…', stopped: '回复已停止。',
            interrupted: '回复已中断。你可以重试。', stop: '停止', send: '发送',
            you: '你', eyeball: 'EYEBALL', safeError: 'Eyeball 暂时不可用。请稍后重试。',
            invitation: '对这个产品有疑问？询问 Eyeball。', invitationLabel: '可选的 Eyeball 邀请',
            dismissInvitation: '在本次访问中关闭 Eyeball 邀请',
            clarificationLabel: 'Eyeball 澄清选项', clarificationSomethingElse: '其他意思'
        })
    })
});

export function mapBrowserLocale(languages = []) {
    for (const value of languages) {
        if (typeof value !== 'string') continue;
        const tag = value.toLowerCase();
        if (tag === 'en' || tag.startsWith('en-')) return 'en';
        if (tag === 'es' || tag.startsWith('es-')) return 'es';
        if (tag === 'fr' || tag.startsWith('fr-')) return 'fr';
        if (tag === 'ar' || tag.startsWith('ar-')) return 'ar';
        if (tag === 'zh-cn' || tag === 'zh-hans' || tag.startsWith('zh-hans-') || tag === 'zh-sg') return 'zh-CN';
    }
    return DEFAULT_EYEBALL_LOCALE;
}

export function initialEyeballLocale(storage, languages = []) {
    try {
        const saved = storage?.getItem(EYEBALL_LOCALE_STORAGE_KEY);
        if (Object.hasOwn(EYEBALL_LOCALES, saved)) return saved;
    } catch { /* Storage can be blocked without breaking chat. */ }
    return mapBrowserLocale(languages);
}

export function persistEyeballLocale(storage, locale) {
    if (!Object.hasOwn(EYEBALL_LOCALES, locale)) return false;
    try {
        storage?.setItem(EYEBALL_LOCALE_STORAGE_KEY, locale);
        return true;
    } catch { return false; }
}

export function localeDefinition(locale) {
    return EYEBALL_LOCALES[locale] || EYEBALL_LOCALES[DEFAULT_EYEBALL_LOCALE];
}

export function shouldRefocusEyeballComposer(interactionMode, coarsePointer) {
    return interactionMode !== 'touch' && !coarsePointer;
}
