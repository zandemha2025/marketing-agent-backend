/**
 * API service for communicating with the backend.
 */

// Use environment variable, or empty string to use Vite's proxy in development
const API_BASE_URL = (import.meta.env.VITE_API_URL || '') + '/api';

class ApiService {
    constructor() {
        this.baseUrl = API_BASE_URL;
        this.onError = null;
    }

    setErrorHandler(handler) {
        this.onError = handler;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;

        // Add auth token if available
        const authToken = this.getAuthToken();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }

        const config = {
            ...options,
            headers,
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                let errorMessage = `HTTP error ${response.status}`;
                try {
                    const error = await response.json();
                    errorMessage = error.detail || error.message || errorMessage;
                } catch {
                    // Ignore JSON parse error
                }

                const userMessage = this.getUserFriendlyError(response.status, errorMessage);
                const error = new Error(userMessage);
                error.status = response.status;
                error.originalMessage = errorMessage;

                if (this.onError) {
                    this.onError(userMessage, response.status);
                }

                throw error;
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
                const networkError = new Error('Unable to connect to server. Please check your connection.');
                if (this.onError) {
                    this.onError(networkError.message, 0);
                }
                throw networkError;
            }
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    getUserFriendlyError(status, originalMessage) {
        // For 400/422 validation errors, prefer the actual backend message
        // so users know what field(s) need fixing
        if (status === 400 || status === 422) {
            return originalMessage || 'Invalid request. Please check your input.';
        }

        const errorMap = {
            401: 'Please log in to continue.',
            403: 'You don\'t have permission for this action.',
            404: 'The requested resource was not found.',
            429: 'Too many requests. Please wait a moment.',
            500: 'Server error. Our team has been notified.',
            502: 'Server is temporarily unavailable. Please try again.',
            503: 'Service is temporarily unavailable. Please try again in a moment.',
        };
        return errorMap[status] || originalMessage;
    }

    // Onboarding endpoints
    async startOnboarding(domain, companyName = null) {
        return this.request('/onboarding/start', {
            method: 'POST',
            body: JSON.stringify({
                domain,
                company_name: companyName,
            }),
        });
    }

    async getOnboardingStatus(organizationId) {
        return this.request(`/onboarding/status/${organizationId}`);
    }

    async getOnboardingResult(organizationId) {
        return this.request(`/onboarding/result/${organizationId}`);
    }

    async updateOnboardingResult(organizationId, section, data) {
        return this.request(`/onboarding/result/${organizationId}`, {
            method: 'PUT',
            body: JSON.stringify({ section, data }),
        });
    }

    async retryOnboarding(organizationId) {
        return this.request(`/onboarding/retry/${organizationId}`, {
            method: 'POST',
        });
    }

    // Organization endpoints
    async getOrganization(organizationId) {
        return this.request(`/organizations/${organizationId}`);
    }

    async getKnowledgeBase(organizationId) {
        return this.request(`/organizations/${organizationId}/knowledge-base`);
    }

    async createOrganization(data) {
        return this.request('/organizations/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateOrganization(orgId, data) {
        return this.request(`/organizations/${orgId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    async updateKnowledgeBase(orgId, data) {
        return this.request(`/organizations/${orgId}/knowledge-base`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    // Campaign endpoints
    async listCampaigns(organizationId) {
        return this.request(`/campaigns?organization_id=${organizationId}`);
    }

    async getCampaign(campaignId) {
        return this.request(`/campaigns/${campaignId}`);
    }

    async createCampaign(data) {
        return this.request('/campaigns', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async executeCampaign(campaignId) {
        return this.request(`/campaigns/${campaignId}/execute`, {
            method: 'POST',
        });
    }

    async selectConcept(campaignId, conceptIndex) {
        return this.request(`/campaigns/${campaignId}/select-concept`, {
            method: 'POST',
            body: JSON.stringify({ concept_index: conceptIndex }),
        });
    }

    async regenerateAsset(campaignId, assetIndex, modifications) {
        return this.request(`/campaigns/${campaignId}/regenerate-asset`, {
            method: 'POST',
            body: JSON.stringify({ asset_index: assetIndex, modifications }),
        });
    }

    async updateCampaign(campaignId, data) {
        return this.request(`/campaigns/${campaignId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteCampaign(campaignId) {
        return this.request(`/campaigns/${campaignId}`, {
            method: 'DELETE',
        });
    }

    // Asset endpoints
    async listAssets(campaignId) {
        return this.request(`/assets?campaign_id=${campaignId}`);
    }

    async getAsset(assetId) {
        return this.request(`/assets/${assetId}`);
    }

    async getAssetVersions(assetId) {
        return this.request(`/assets/${assetId}/versions`);
    }

    async updateAsset(assetId, data) {
        return this.request(`/assets/${assetId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteAsset(assetId) {
        return this.request(`/assets/${assetId}`, {
            method: 'DELETE',
        });
    }

    async createAsset(data) {
        return this.request('/assets/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getAssetComments(assetId) {
        return this.request(`/assets/${assetId}/comments`);
    }

    async addAssetComment(assetId, data) {
        return this.request(`/assets/${assetId}/comments`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // Chat endpoints
    async listConversations(organizationId) {
        return this.request(`/chat/conversations?organization_id=${organizationId}`);
    }

    async getConversation(conversationId) {
        return this.request(`/chat/conversations/${conversationId}`);
    }

    async createConversation(organizationId, title, contextType) {
        return this.request('/chat/conversations', {
            method: 'POST',
            body: JSON.stringify({
                organization_id: organizationId,
                title,
                context_type: contextType,
            }),
        });
    }

    async deleteConversation(conversationId) {
        return this.request(`/chat/conversations/${conversationId}`, {
            method: 'DELETE',
        });
    }

    async sendMessage(conversationId, content) {
        return this.request(`/chat/conversations/${conversationId}/messages?stream=false`, {
            method: 'POST',
            body: JSON.stringify({ content }),
        });
    }

    async streamMessage(conversationId, content, onChunk, onDone) {
        const url = `${this.baseUrl}/chat/conversations/${conversationId}/messages?stream=true`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP error ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;
                    try {
                        const parsed = JSON.parse(data);
                        const text = parsed.content || parsed.text || data;
                        fullText += text;
                        if (onChunk) onChunk(text);
                    } catch {
                        fullText += data;
                        if (onChunk) onChunk(data);
                    }
                }
            }
        }

        if (onDone) onDone(fullText);
        return fullText;
    }

    // WebSocket for real-time updates
    _connectWebSocket(path, onMessage, onError) {
        let wsUrl;
        if (this.baseUrl.startsWith('http://') || this.baseUrl.startsWith('https://')) {
            // Absolute URL - convert protocol
            wsUrl = this.baseUrl
                .replace('http://', 'ws://')
                .replace('https://', 'wss://');
        } else {
            // Relative URL (e.g., '/api') - construct from window.location
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            wsUrl = `${protocol}//${window.location.host}${this.baseUrl}`;
        }

        const ws = new WebSocket(`${wsUrl}${path}`);

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage(data);
            } catch (error) {
                console.error('WebSocket message parse error:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            if (onError) onError(error);
        };

        ws.onclose = () => {
            console.log('WebSocket closed');
        };

        const pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send('ping');
            }
        }, 30000);

        return {
            ws,
            close: () => {
                clearInterval(pingInterval);
                ws.close();
            },
        };
    }

    connectOnboardingProgress(organizationId, onMessage, onError) {
        return this._connectWebSocket(
            `/onboarding/progress/${organizationId}`,
            onMessage,
            onError
        );
    }

    connectCampaignExecution(campaignId, sessionId, onMessage, onError) {
        return this._connectWebSocket(
            `/campaigns/${campaignId}/ws/${sessionId}`,
            onMessage,
            onError
        );
    }

    connectChat(conversationId, onMessage, onError) {
        return this._connectWebSocket(
            `/chat/conversations/${conversationId}/ws`,
            onMessage,
            onError
        );
    }

    // --- Deliverables ---
    
    async listDeliverables(campaignId) {
        return this.request(`/deliverables/?campaign_id=${campaignId}`);
    }

    async getDeliverable(deliverableId) {
        return this.request(`/deliverables/${deliverableId}`);
    }

    async createDeliverable(deliverableData) {
        return this.request('/deliverables/', {
            method: 'POST',
            body: JSON.stringify(deliverableData),
        });
    }

    async updateDeliverable(deliverableId, deliverableData) {
        return this.request(`/deliverables/${deliverableId}`, {
            method: 'PUT',
            body: JSON.stringify(deliverableData),
        });
    }

    async deleteDeliverable(deliverableId) {
        return this.request(`/deliverables/${deliverableId}`, {
            method: 'DELETE',
        });
    }

    async refineContent(text, action, type) {
        return this.request('/deliverables/refine', {
            method: 'POST',
            body: JSON.stringify({ text, action, type }),
        });
    }

    // --- Trends (TrendMaster) ---

    async listTrends(organizationId, category = null) {
        let url = `/trends/?organization_id=${organizationId}`;
        if (category && category !== 'All') url += `&category=${category}`;
        return this.request(url);
    }

    async getTrend(trendId) {
        return this.request(`/trends/${trendId}`);
    }

    async createTrend(data) {
        return this.request('/trends/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateTrend(trendId, data) {
        return this.request(`/trends/${trendId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async deleteTrend(trendId) {
        return this.request(`/trends/${trendId}`, {
            method: 'DELETE',
        });
    }

    async listAnalyzedTrends(organizationId, category = null, minRelevance = 0) {
        let url = `/trends/analyzed?organization_id=${organizationId}`;
        if (category && category !== 'All') url += `&category=${category}`;
        if (minRelevance > 0) url += `&min_relevance=${minRelevance}`;
        return this.request(url);
    }

    async refreshTrends(organizationId) {
        return this.request(`/trends/refresh?organization_id=${organizationId}`, {
            method: 'POST',
        });
    }

    async getTrendCategories() {
        return this.request('/trends/categories');
    }

    async createContentFromTrend(organizationId, trendData) {
        return this.request(`/trends/create-content?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(trendData),
        });
    }

    // --- Image Editor ---
    
    async listImageEditSessions(organizationId, campaignId = null, deliverableId = null) {
        const params = new URLSearchParams({ organization_id: organizationId });
        if (campaignId) params.append('campaign_id', campaignId);
        if (deliverableId) params.append('deliverable_id', deliverableId);
        return this.request(`/image-editor/sessions?${params}`);
    }

    async createImageEditSession(sessionData, organizationId) {
        return this.request(`/image-editor/sessions?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(sessionData),
        });
    }

    async getImageEditSession(sessionId) {
        return this.request(`/image-editor/sessions/${sessionId}`);
    }

    async updateImageEditSession(sessionId, sessionData) {
        return this.request(`/image-editor/sessions/${sessionId}`, {
            method: 'PATCH',
            body: JSON.stringify(sessionData),
        });
    }

    async deleteImageEditSession(sessionId) {
        return this.request(`/image-editor/sessions/${sessionId}`, {
            method: 'DELETE',
        });
    }

    async addImageEditHistory(sessionId, historyData) {
        return this.request(`/image-editor/sessions/${sessionId}/history`, {
            method: 'POST',
            body: JSON.stringify(historyData),
        });
    }

    async getImageEditHistory(sessionId) {
        return this.request(`/image-editor/sessions/${sessionId}/history`);
    }

    async generateImage(generationRequest) {
        return this.request('/image-editor/generate', {
            method: 'POST',
            body: JSON.stringify(generationRequest),
        });
    }

    async editImage(editRequest, sessionId = null) {
        const params = new URLSearchParams();
        if (sessionId) params.append('session_id', sessionId);
        return this.request(`/image-editor/edit?${params}`, {
            method: 'POST',
            body: JSON.stringify(editRequest),
        });
    }

    // --- Kata (Video/AI Content) ---

    async createSyntheticInfluencer(data) {
        return this.request('/kata/synthetic-influencer', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async compositeProduct(data) {
        return this.request('/kata/composite-product', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async mergeVideos(data) {
        return this.request('/kata/merge-videos', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async applyUGCStyle(data) {
        return this.request('/kata/ugc-style', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async generateVoice(data) {
        return this.request('/kata/generate-voice', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getKataJobStatus(jobId) {
        return this.request(`/kata/jobs/${jobId}`);
    }

    async getKataJobResult(jobId) {
        return this.request(`/kata/jobs/${jobId}/result`);
    }

    async listKataJobs(status = null) {
        let url = '/kata/jobs';
        if (status) url += `?status=${status}`;
        return this.request(url);
    }

    async generateScript(data) {
        return this.request('/kata/generate-script', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async listInfluencers(organizationId) {
        return this.request(`/kata/influencers?organization_id=${organizationId}`);
    }

    // --- Uploads ---

    async uploadFile(file, type = 'image', onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type);

        const url = `${this.baseUrl}/uploads/`;
        const authToken = this.getAuthToken();

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            if (onProgress) {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const progress = (event.loaded / event.total) * 100;
                        onProgress(progress);
                    }
                });
            }

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('Invalid response from server'));
                    }
                } else {
                    let errorMessage = `Upload failed: ${xhr.status}`;
                    try {
                        const error = JSON.parse(xhr.responseText);
                        errorMessage = error.detail || error.message || errorMessage;
                    } catch {
                        // Ignore parse error
                    }
                    reject(new Error(errorMessage));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });

            xhr.open('POST', url);
            if (authToken) {
                xhr.setRequestHeader('Authorization', `Bearer ${authToken}`);
            }
            xhr.send(formData);
        });
    }

    async uploadImage(file, onProgress = null) {
        return this.uploadFile(file, 'image', onProgress);
    }

    async uploadVideo(file, onProgress = null) {
        return this.uploadFile(file, 'video', onProgress);
    }

    async uploadDocument(file, onProgress = null) {
        return this.uploadFile(file, 'document', onProgress);
    }

    async getPresignedUploadUrl(filename, contentType, type = 'image') {
        return this.request('/uploads/presigned-url', {
            method: 'POST',
            body: JSON.stringify({ filename, content_type: contentType, type }),
        });
    }

    async deleteFile(fileKey) {
        return this.request(`/uploads/${encodeURIComponent(fileKey)}`, {
            method: 'DELETE',
        });
    }

    // --- Content Generation ---

    async generatePressRelease(organizationId, data) {
        return this.request(`/content/press-release?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async generateHeadlineVariants(organizationId, data) {
        return this.request(`/content/press-release/headlines?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async generateQuote(organizationId, data) {
        return this.request(`/content/press-release/quote?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async processInterview(organizationId, data) {
        return this.request(`/content/interview/process?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async generateContentFromInterview(organizationId, data) {
        return this.request(`/content/interview/generate-content?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async generateEmail(organizationId, data) {
        return this.request(`/content/email/generate?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async generateSubjectVariants(organizationId, data) {
        return this.request(`/content/email/subject-variants?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getEmailTemplates() {
        return this.request('/content/email/templates');
    }

    async generateLandingPage(organizationId, data) {
        return this.request(`/content/landing-page/generate?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async scaffoldLandingPageProject(organizationId, data) {
        return this.request(`/content/landing-page/scaffold?organization_id=${organizationId}`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // --- Tasks (Kanban) ---
    
    async listTasks(organizationId, campaignId = null) {
        let url = `/tasks/?organization_id=${organizationId}`;
        if (campaignId) url += `&campaign_id=${campaignId}`;
        return this.request(url);
    }

    async getTask(taskId) {
        return this.request(`/tasks/${taskId}`);
    }

    async createTask(taskData) {
        return this.request('/tasks/', {
            method: 'POST',
            body: JSON.stringify(taskData),
        });
    }

    async updateTask(taskId, taskData) {
        return this.request(`/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify(taskData),
        });
    }

    async updateTaskStatus(taskId, status) {
        return this.request(`/tasks/${taskId}/status?status=${status}`, {
            method: 'PATCH',
        });
    }

    async deleteTask(taskId) {
        return this.request(`/tasks/${taskId}`, {
            method: 'DELETE',
        });
    }

    // --- Social Calendar ---

    async listScheduledPosts(organizationId, start = null, end = null) {
        let url = `/scheduled-posts/?organization_id=${organizationId}`;
        if (start) url += `&start_date=${start.toISOString()}`;
        if (end) url += `&end_date=${end.toISOString()}`;
        return this.request(url);
    }

    async getScheduledPost(postId) {
        return this.request(`/scheduled-posts/${postId}`);
    }

    async createScheduledPost(postData) {
        return this.request('/scheduled-posts/', {
            method: 'POST',
            body: JSON.stringify(postData),
        });
    }

    async updateScheduledPost(postId, postData) {
        return this.request(`/scheduled-posts/${postId}`, {
            method: 'PUT',
            body: JSON.stringify(postData),
        });
    }

    async deleteScheduledPost(postId) {
        return this.request(`/scheduled-posts/${postId}`, {
            method: 'DELETE',
        });
    }

    async publishPost(postId) {
        return this.request(`/scheduled-posts/${postId}/publish`, {
            method: 'POST',
        });
    }

    // --- Auth ---

    async register(email, password, name, organizationName = null) {
        const response = await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                email,
                password,
                name,
                organization_name: organizationName
            }),
        });
        // Store token if returned (same as login)
        if (response.access_token) {
            localStorage.setItem('authToken', response.access_token);
        }
        if (response.user?.organization_id) {
            localStorage.setItem('organizationId', response.user.organization_id);
        }
        return response;
    }

    async login(email, password) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        // Store token and org ID if returned
        if (response.access_token) {
            localStorage.setItem('authToken', response.access_token);
        }
        if (response.user?.organization_id) {
            localStorage.setItem('organizationId', response.user.organization_id);
        }
        return response;
    }

    async getMe() {
        return this.request('/auth/me');
    }

    logout() {
        localStorage.removeItem('authToken');
        localStorage.removeItem('organizationId');
    }

    async refreshToken() {
        // Backend doesn't have refresh endpoint, but add placeholder for future
        // For now, re-authenticate by calling getMe()
        return this.getMe();
    }

    isAuthenticated() {
        return !!localStorage.getItem('authToken');
    }

    // Analytics endpoints
    async getAnalyticsOverview(organizationId, days = 30) {
        return this.request(`/analytics/overview?organization_id=${organizationId}&days=${days}`);
    }

    async getAttributionReport(data) {
        return this.request('/analytics/attribution/report', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getCampaignAnalytics(organizationId, days = 30) {
        return this.request(`/analytics/campaigns?organization_id=${organizationId}&days=${days}`);
    }

    async getAssetAnalytics(organizationId, days = 30) {
        return this.request(`/analytics/assets?organization_id=${organizationId}&days=${days}`);
    }

    async getTaskAnalytics(organizationId, days = 30) {
        return this.request(`/analytics/tasks?organization_id=${organizationId}&days=${days}`);
    }

    async getPostAnalytics(organizationId, days = 30) {
        return this.request(`/analytics/posts?organization_id=${organizationId}&days=${days}`);
    }

    async getRecentActivity(organizationId, limit = 20) {
        return this.request(`/analytics/activity?organization_id=${organizationId}&limit=${limit}`);
    }

    async getDeliverablesByType(organizationId) {
        return this.request(`/analytics/deliverables/by-type?organization_id=${organizationId}`);
    }

    async getDeliverablesByStatus(organizationId) {
        return this.request(`/analytics/deliverables/by-status?organization_id=${organizationId}`);
    }

    async getPostsByPlatform(organizationId) {
        return this.request(`/analytics/posts/by-platform?organization_id=${organizationId}`);
    }

    async getCampaignProgress(organizationId) {
        return this.request(`/analytics/campaigns/progress?organization_id=${organizationId}`);
    }

    async getActivityTimeline(organizationId, days = 30) {
        return this.request(`/analytics/activity/timeline?organization_id=${organizationId}&days=${days}`);
    }

    // User management endpoints
    async listUsers(organizationId, page = 1, pageSize = 20) {
        return this.request(`/users/?organization_id=${organizationId}&page=${page}&page_size=${pageSize}`);
    }

    async getUser(userId) {
        return this.request(`/users/${userId}`);
    }

    async inviteUser(inviteData) {
        return this.request('/users/invite', {
            method: 'POST',
            body: JSON.stringify(inviteData),
        });
    }

    async createUser(userData) {
        return this.request('/users/', {
            method: 'POST',
            body: JSON.stringify(userData),
        });
    }

    async updateUser(userId, userData) {
        return this.request(`/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData),
        });
    }

    async updateProfile(profileData) {
        return this.request('/users/me/profile', {
            method: 'PUT',
            body: JSON.stringify(profileData),
        });
    }

    async changePassword(currentPassword, newPassword) {
        return this.request('/users/me/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
            }),
        });
    }

    async deactivateUser(userId) {
        return this.request(`/users/${userId}/deactivate`, {
            method: 'POST',
        });
    }

    async activateUser(userId) {
        return this.request(`/users/${userId}/activate`, {
            method: 'POST',
        });
    }

    async deleteUser(userId) {
        return this.request(`/users/${userId}`, {
            method: 'DELETE',
        });
    }

    async listRoles() {
        return this.request('/users/roles/list');
    }

    async getUserStats(organizationId) {
        return this.request(`/users/stats/overview?organization_id=${organizationId}`);
    }

    // Halftime/Kata Video Engine endpoints
    async analyzeVideoForPlacement(videoUrl, numKeyframes = 8) {
        return this.request('/kata/halftime/analyze', {
            method: 'POST',
            body: JSON.stringify({
                video_url: videoUrl,
                num_keyframes: numKeyframes,
            }),
        });
    }

    async detectInsertionZones(videoUrl, productType, options = {}) {
        return this.request('/kata/halftime/detect-zones', {
            method: 'POST',
            body: JSON.stringify({
                video_url: videoUrl,
                product_type: productType,
                product_size: options.productSize || 'medium',
                placement_style: options.placementStyle || 'natural',
            }),
        });
    }

    async compositeProductIntoVideo(videoUrl, productDescription, options = {}) {
        return this.request('/kata/halftime/composite', {
            method: 'POST',
            body: JSON.stringify({
                video_url: videoUrl,
                product_description: productDescription,
                product_type: options.productType || 'product',
                platform: options.platform || 'tiktok',
                style: options.style || 'natural',
                ugc_effects: options.ugcEffects || false,
                start_time: options.startTime || 0,
                duration: options.duration || null,
            }),
        });
    }

    async createQuickUGCVideo(videoUrl, productDescription, options = {}) {
        return this.request('/kata/halftime/quick-ugc', {
            method: 'POST',
            body: JSON.stringify({
                video_url: videoUrl,
                product_description: productDescription,
                product_type: options.productType || 'product',
                platform: options.platform || 'tiktok',
                style: 'ugc',
                ugc_effects: true,
                start_time: options.startTime || 0,
                duration: options.duration || null,
            }),
        });
    }

    async getHalftimeJobStatus(jobId) {
        return this.request(`/kata/halftime/job/${jobId}`);
    }

    getAuthToken() {
        return localStorage.getItem('authToken');
    }
}

export const api = new ApiService();
export default api;
