import { API_BASE_URL } from '../config/index';


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


export async function handleResponse<T>(response: Response): Promise<T> {
    if (response.ok)
        return response.json();

    // ---------------------------------------------------------------
    // response not okay, now doing error handling process
    // ---------------------------------------------------------------
    let apiError = await parseRawError({ response });

    console.log('API Error: Message:', apiError.message, 'Status:', apiError.status, 'Data:', apiError.data);
    throw apiError;
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
        const response = await fetch(fullUrl, config);
        return await handleResponse<T>(response);
    } catch (fetchError) {
        // If it's already an ApiError from handleResponse, re-throw it as-is
        if (fetchError instanceof ApiError) {
            throw fetchError;
        }
        // Only wrap actual network errors
        throw new Error(`Network error: ${(fetchError as any)?.message || String(fetchError)}`);
    }
}