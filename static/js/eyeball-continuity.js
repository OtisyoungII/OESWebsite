// Server-issued lookup continuity is opaque. Browser prose never assigns capability authority.
export function completionDirective(data) {
    if (!data || typeof data !== 'object' || Array.isArray(data) ||
            Object.keys(data).some(key => !['continuation', 'history', 'company_topic'].includes(key))) {
        throw new Error('invalid completion metadata');
    }
    if (data.continuation !== undefined &&
            (typeof data.continuation !== 'string' || !/^[0-9a-f]{64}$/.test(data.continuation))) {
        throw new Error('invalid continuation');
    }
    if (data.history !== undefined && data.history !== 'exclude_exchange') {
        throw new Error('invalid history directive');
    }
    if (data.company_topic !== undefined && (data.history !== 'exclude_exchange' ||
            typeof data.company_topic !== 'string' || !/^[0-9a-f]{64}$/.test(data.company_topic))) {
        throw new Error('invalid company topic marker');
    }
    return {
        continuation: data.continuation || null,
        ...(data.company_topic ? { companyTopic: data.company_topic } : {}),
        retainExchange: data.history !== 'exclude_exchange',
    };
}
