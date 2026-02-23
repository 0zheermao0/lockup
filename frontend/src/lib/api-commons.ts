import { API_BASE_URL } from '../config/index';
import { useAuthStore } from '../stores/auth';


export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
        public data?: any
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

async function parseRawError(error: any): Promise<ApiError> {

    // if network crashed/abort/timeout
    if (
        error?.code === 'ECONNABORTED' ||      // axios
        error?.name === 'AbortError' ||        // fetch
        error?.message?.toLowerCase().includes('timeout')
    ) {
        return new ApiError('Request timeout', 0, error);
    }

    // if there is no response (e.g., network error)
    if (!error?.response) {
        return new ApiError('Network connection failed', 0, error);
    }

    const status = error.response.status;

    // transform response data into json object
    let error_resp_data: any = null;

    // axios: response.data already parsed
    if (typeof error.response.data === 'object') {
        error_resp_data = error.response.data;
    }
    // fetch: need to call json()
    else if (typeof error.response.json === 'function') {
        error_resp_data = await error.response.json().catch(() => null);
    }

    // resp data is json object
    if (error_resp_data && typeof error_resp_data === 'object') {
        // find message key words from common fields  
        if (error_resp_data.error) {
            return new ApiError(error_resp_data.error, status, error_resp_data);
        }

        if (error_resp_data.message) {
            return new ApiError(error_resp_data.message, status, error_resp_data);
        }

        if (error_resp_data.detail) {
            return new ApiError(error_resp_data.detail, status, error_resp_data);
        }

        if (error_resp_data.non_field_errors) {
            return Array.isArray(error_resp_data.non_field_errors)
                ? new ApiError(error_resp_data.non_field_errors[0], status, error_resp_data)
                : new ApiError(error_resp_data.non_field_errors, status, error_resp_data);
        }

        if (error_resp_data.reason) {
            return new ApiError(error_resp_data.reason, status, error_resp_data);
        }

        if (error_resp_data.error_description) {
            return new ApiError(error_resp_data.error_description, status, error_resp_data);
        }

        // check for field-specific errors
        const fieldErrors = Object.keys(error_resp_data).filter(key =>
            key != "code" && Array.isArray(error_resp_data[key])
        );
        if (fieldErrors.length > 0) {
            const firstField = fieldErrors[0];
            if (firstField) {
                const fieldErrorArray = error_resp_data[firstField];
                if (Array.isArray(fieldErrorArray) && fieldErrorArray.length > 0) {
                    const firstError = fieldErrorArray[0];
                    return new ApiError(`${firstField}: ${firstError}`, status, error_resp_data);
                }
            }
        }

        if (error_resp_data.code) {
            return new ApiError(error_resp_data.code, status, error_resp_data);
        }
    }

    // json conversion failed or empty body, return http code
    if (status == 401) {
        return new ApiError('AUTHENTICATION_REQUIRED', status, error);
    }
    if (status == 403) {
        return new ApiError('PERMISSION_DENIED', status, error);
    }
    if (status == 429) {
        return new ApiError('RATE_LIMIT_EXCEEDED', status, error);
    }
    return new ApiError(`HTTP ${status} Error`, status, error);
}


export async function handleResponse<T>(response: Response, requestUrl?: string): Promise<T> {
    if (response.ok) {
        // Handle responses with no content (like DELETE requests)
        if (response.status === 204 || response.headers.get('content-length') === '0') {
            return null as T;
        }

        try {
            const data = await response.json();

            // 状态同步拦截器 - 自动同步后端返回的积分和锁定状态更新
            if (data && typeof data === 'object') {
                try {
                    // 使用authStore同步状态
                    const authStore = useAuthStore();

                    // 检查各种积分字段并同步
                    if (data.remaining_coins !== undefined) {
                        authStore.updateCoins(data.remaining_coins);
                    } else if (data.user_remaining_coins !== undefined) {
                        authStore.updateCoins(data.user_remaining_coins);
                    } else if (data.user_total_coins !== undefined) {
                        authStore.updateCoins(data.user_total_coins);
                    }

                    // 检查锁定状态字段并同步 - 只对当前用户的端点更新
                    // Define endpoints that should update current user's lock task
                    const CURRENT_USER_ENDPOINTS = [
                        '/auth/me/',
                        '/auth/profile/',
                        '/auth/login/',
                        '/auth/register/',
                        '/tasks/',
                        '/store/'
                    ];

                    const shouldUpdateLockTask = (url: string) => {
                        // Exclude profile endpoints that fetch other users' data
                        if (url.match(/\/auth\/users\/\d+\//)) {
                            return false;
                        }
                        return CURRENT_USER_ENDPOINTS.some(endpoint => url.includes(endpoint));
                    };

                    const url = requestUrl || '';

                    if (data.active_lock_task !== undefined && shouldUpdateLockTask(url)) {
                        // Only update if it's the current user's task or during login/register
                        const isAuthEndpoint = url.includes('/auth/login/') || url.includes('/auth/register/');
                        if (!data.user || isAuthEndpoint || (authStore.user && data.user.id === authStore.user.id)) {
                            authStore.updateActiveLockTask(data.active_lock_task);
                        }
                    } else if (data.user && data.user.active_lock_task !== undefined && shouldUpdateLockTask(url)) {
                        // Only update if it's the current user or during login/register
                        const isAuthEndpoint = url.includes('/auth/login/') || url.includes('/auth/register/');
                        if (isAuthEndpoint || (authStore.user && data.user.id === authStore.user.id)) {
                            authStore.updateActiveLockTask(data.user.active_lock_task);
                        }
                    }
                } catch (storeError) {
                    console.warn('Error updating auth store:', storeError);
                    // Continue processing the response even if store update fails
                }
            }

            return data;
        } catch (jsonError) {
            throw new ApiError('Failed to parse response JSON', response.status, jsonError);
        }
    }

    // ---------------------------------------------------------------
    // response not okay, now doing error handling process
    // ---------------------------------------------------------------
    const apiError = await parseRawError({ response });

    console.log('API Error: Message:', apiError.message, 'Status:', apiError.status, 'Data:', apiError.data);
    throw apiError;
}

async function fetchWithTimeout(input: RequestInfo, init?: RequestInit, timeoutMs = 10000): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(input, {
            ...init,
            signal: controller.signal
        });
        return response;
    } finally {
        clearTimeout(timeoutId);
    }
}

export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const token = localStorage.getItem('token');
    const fullUrl = `${API_BASE_URL}${endpoint}`;

    const config: RequestInit = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { Authorization: `Token ${token}` }),
            ...options.headers,
        },
        ...options,
    };

    try {
        const response = await fetchWithTimeout(fullUrl, config);
        return await handleResponse<T>(response, endpoint);
    } catch (fetchError) {
        // If it's already an ApiError from handleResponse, re-throw it as-is
        if (fetchError instanceof ApiError) {
            throw fetchError;
        }
        // dont wrap, the parseRawError can handle it
        const apiError = await parseRawError(fetchError);
        throw apiError;
    }
}