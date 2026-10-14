// Server-issued lookup continuity is opaque. Browser prose never assigns capability authority.
export function completionDirective(data) {
    if (!data || typeof data !== 'object' || Array.isArray(data) ||
            Object.keys(data).some(key => !['continuation', 'history'].includes(key))) {
        throw new Error('invalid completion metadata');
    }
    if (data.continuation !== undefined &&
            (typeof data.continuation !== 'string' || !/^[0-9a-f]{64}$/.test(data.continuation))) {
        throw new Error('invalid continuation');
    }
    if (data.history !== undefined && data.history !== 'exclude_exchange') {
        throw new Error('invalid history directive');
    }
    return {
        continuation: data.continuation || null,
        retainExchange: data.history !== 'exclude_exchange',
    };
}
