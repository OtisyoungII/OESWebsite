const reasons = new Set(['ambiguous_typo', 'high_impact_ambiguity', 'low_confidence']);
const tokenPattern = /^[0-9a-f]{64}$/;

export function validClarification(value) {
    if (!value || typeof value !== 'object'
            || !Object.keys(value).every(key => ['prompt', 'reason', 'choices'].includes(key))
            || Object.keys(value).length !== 3
            || !reasons.has(value.reason) || typeof value.prompt !== 'string'
            || !value.prompt.trim() || value.prompt.length > 240
            || !Array.isArray(value.choices) || value.choices.length > 3) return false;
    return value.choices.every(choice => choice && typeof choice === 'object'
        && Object.keys(choice).length === 2
        && typeof choice.label === 'string' && choice.label.trim() === choice.label
        && choice.label.length > 0 && choice.label.length <= 96
        && typeof choice.token === 'string' && tokenPattern.test(choice.token));
}

export function renderClarification(document, value, strings, handlers) {
    if (!validClarification(value)) throw new Error('invalid clarification');
    const card = document.createElement('section');
    card.className = 'eyeball-clarification';
    card.setAttribute('aria-label', strings.clarificationLabel);
    const prompt = document.createElement('p');
    prompt.textContent = value.prompt;
    const choices = document.createElement('div');
    choices.className = 'eyeball-clarification__choices';
    const letters = ['A', 'B', 'C'];
    let resolved = false;
    const resolve = callback => {
        if (resolved) return;
        resolved = true;
        card.dataset.resolved = 'true';
        choices.querySelectorAll('button').forEach(button => { button.disabled = true; });
        callback();
    };
    value.choices.forEach((choice, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.clarificationToken = choice.token;
        button.textContent = `${letters[index]}  ${choice.label}`;
        button.setAttribute('aria-label', `${letters[index]}. ${choice.label}`);
        button.addEventListener('click', () => resolve(() => handlers.select(choice)));
        choices.append(button);
    });
    const other = document.createElement('button');
    other.type = 'button';
    other.className = 'eyeball-clarification__other';
    other.textContent = `${letters[value.choices.length]}  ${strings.clarificationSomethingElse}`;
    other.setAttribute('aria-label', strings.clarificationSomethingElse);
    other.addEventListener('click', () => resolve(handlers.rephrase));
    choices.append(other);
    card.append(prompt, choices);
    return card;
}
