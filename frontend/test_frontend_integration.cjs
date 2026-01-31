/**
 * Frontend Integration Test Script
 * 
 * Tests API connectivity from frontend perspective
 * Verifies all API endpoints are reachable
 * Checks for CORS issues
 * 
 * Run with: node test_frontend_integration.js
 */

const fs = require('fs');
const path = require('path');

// Configuration
const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000';
const API_URL = `${API_BASE_URL}/api`;

// Test results storage
const results = {
    timestamp: new Date().toISOString(),
    api_base_url: API_URL,
    tests: [],
    summary: {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0
    }
};

// Helper function to make API requests
async function testEndpoint(name, method, endpoint, options = {}) {
    const url = `${API_URL}${endpoint}`;
    const testResult = {
        name,
        method,
        endpoint,
        url,
        status: 'pending',
        statusCode: null,
        responseTime: null,
        error: null,
        corsHeaders: null
    };

    const startTime = Date.now();

    try {
        const fetchOptions = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:5173', // Simulate frontend origin
                ...options.headers
            },
            ...options
        };

        if (options.body) {
            fetchOptions.body = JSON.stringify(options.body);
        }

        const response = await fetch(url, fetchOptions);
        testResult.responseTime = Date.now() - startTime;
        testResult.statusCode = response.status;

        // Check CORS headers
        testResult.corsHeaders = {
            'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
            'access-control-allow-methods': response.headers.get('access-control-allow-methods'),
            'access-control-allow-headers': response.headers.get('access-control-allow-headers')
        };

        // Consider 2xx, 401, 403, 404 as "reachable" (API is working)
        if (response.status >= 200 && response.status < 500) {
            testResult.status = 'passed';
        } else {
            testResult.status = 'failed';
            testResult.error = `Unexpected status code: ${response.status}`;
        }

        // Try to parse response
        try {
            const data = await response.json();
            testResult.responsePreview = JSON.stringify(data).substring(0, 200);
        } catch {
            testResult.responsePreview = 'Non-JSON response';
        }

    } catch (error) {
        testResult.responseTime = Date.now() - startTime;
        testResult.status = 'failed';
        testResult.error = error.message;

        // Check if it's a CORS error
        if (error.message.includes('CORS') || error.message.includes('fetch')) {
            testResult.corsIssue = true;
        }
    }

    results.tests.push(testResult);
    return testResult;
}

// Test suites organized by workstream
const testSuites = {
    // Core API Health
    health: [
        { name: 'API Health Check', method: 'GET', endpoint: '/health' },
        { name: 'API Root', method: 'GET', endpoint: '/' },
    ],

    // Workstream 1: Brand Onboarding
    onboarding: [
        { name: 'Onboarding Start', method: 'POST', endpoint: '/onboarding/start', body: { domain: 'test.com' } },
    ],

    // Workstream 2: Campaign Studio
    campaigns: [
        { name: 'List Campaigns', method: 'GET', endpoint: '/campaigns?organization_id=test-org' },
    ],

    // Workstream 3: AI Chat
    chat: [
        { name: 'List Conversations', method: 'GET', endpoint: '/chat/conversations?organization_id=test-org' },
    ],

    // Workstream 4: Kata Lab
    kata: [
        { name: 'List Kata Jobs', method: 'GET', endpoint: '/kata/jobs' },
        { name: 'Kata Halftime Analyze', method: 'POST', endpoint: '/kata/halftime/analyze', body: { video_url: 'test', num_keyframes: 4 } },
    ],

    // Workstream 5: Asset Generation
    assets: [
        { name: 'Image Generate', method: 'POST', endpoint: '/image-editor/generate', body: { prompt: 'test' } },
        { name: 'List Image Sessions', method: 'GET', endpoint: '/image-editor/sessions?organization_id=test-org' },
    ],

    // Workstream 6: Landing Pages
    landingPages: [
        { name: 'Generate Landing Page', method: 'POST', endpoint: '/content/landing-page/generate?organization_id=test-org', body: { goal: 'test', target_audience: 'test', key_benefits: ['test'], sections: ['hero'] } },
        { name: 'Scaffold Landing Page', method: 'POST', endpoint: '/content/landing-page/scaffold?organization_id=test-org', body: { goal: 'test', target_audience: 'test', key_benefits: ['test'], sections: ['hero'] } },
    ],

    // Workstream 7: Email Marketing
    emailMarketing: [
        { name: 'Generate Email', method: 'POST', endpoint: '/content/email/generate?organization_id=test-org', body: { email_type: 'newsletter', topic: 'test', key_points: ['test'] } },
        { name: 'Email Subject Variants', method: 'POST', endpoint: '/content/email/subject-variants?organization_id=test-org', body: { topic: 'test', count: 3 } },
        { name: 'Email Templates', method: 'GET', endpoint: '/content/email/templates' },
    ],

    // Analytics
    analytics: [
        { name: 'Analytics Overview', method: 'GET', endpoint: '/analytics/overview?organization_id=test-org' },
        { name: 'Campaign Analytics', method: 'GET', endpoint: '/analytics/campaigns?organization_id=test-org' },
    ],

    // Trends
    trends: [
        { name: 'List Trends', method: 'GET', endpoint: '/trends/?organization_id=test-org' },
        { name: 'Trend Categories', method: 'GET', endpoint: '/trends/categories' },
    ],

    // Tasks & Calendar
    tasks: [
        { name: 'List Tasks', method: 'GET', endpoint: '/tasks/?organization_id=test-org' },
        { name: 'List Scheduled Posts', method: 'GET', endpoint: '/scheduled-posts/?organization_id=test-org' },
    ],

    // Auth
    auth: [
        { name: 'Auth Login', method: 'POST', endpoint: '/auth/login', body: { email: 'test@test.com', password: 'test' } },
        { name: 'Auth Register', method: 'POST', endpoint: '/auth/register', body: { email: 'test@test.com', password: 'test', name: 'Test' } },
    ],

    // Deliverables
    deliverables: [
        { name: 'List Deliverables', method: 'GET', endpoint: '/deliverables/?campaign_id=test-campaign' },
    ],

    // Organizations
    organizations: [
        { name: 'Get Organization', method: 'GET', endpoint: '/organizations/test-org' },
        { name: 'Get Knowledge Base', method: 'GET', endpoint: '/organizations/test-org/knowledge-base' },
    ],
};

// Run all tests
async function runTests() {
    console.log('🚀 Starting Frontend Integration Tests');
    console.log(`📡 API Base URL: ${API_URL}`);
    console.log('─'.repeat(60));

    for (const [suiteName, tests] of Object.entries(testSuites)) {
        console.log(`\n📋 Testing: ${suiteName.toUpperCase()}`);
        
        for (const test of tests) {
            const result = await testEndpoint(
                test.name,
                test.method,
                test.endpoint,
                { body: test.body }
            );

            const icon = result.status === 'passed' ? '✅' : '❌';
            const time = result.responseTime ? `${result.responseTime}ms` : 'N/A';
            console.log(`  ${icon} ${test.name} [${result.statusCode || 'ERR'}] (${time})`);
            
            if (result.error) {
                console.log(`     └─ Error: ${result.error}`);
            }
            if (result.corsIssue) {
                console.log(`     └─ ⚠️  CORS Issue Detected`);
            }
        }
    }

    // Calculate summary
    results.summary.total = results.tests.length;
    results.summary.passed = results.tests.filter(t => t.status === 'passed').length;
    results.summary.failed = results.tests.filter(t => t.status === 'failed').length;
    results.summary.skipped = results.tests.filter(t => t.status === 'skipped').length;

    // Print summary
    console.log('\n' + '═'.repeat(60));
    console.log('📊 TEST SUMMARY');
    console.log('═'.repeat(60));
    console.log(`Total Tests: ${results.summary.total}`);
    console.log(`✅ Passed: ${results.summary.passed}`);
    console.log(`❌ Failed: ${results.summary.failed}`);
    console.log(`⏭️  Skipped: ${results.summary.skipped}`);
    console.log(`Pass Rate: ${((results.summary.passed / results.summary.total) * 100).toFixed(1)}%`);

    // Group results by workstream
    const workstreamResults = {};
    for (const [suiteName, tests] of Object.entries(testSuites)) {
        const suiteTests = results.tests.filter(t => 
            tests.some(st => st.name === t.name)
        );
        workstreamResults[suiteName] = {
            total: suiteTests.length,
            passed: suiteTests.filter(t => t.status === 'passed').length,
            failed: suiteTests.filter(t => t.status === 'failed').length
        };
    }
    results.workstreamResults = workstreamResults;

    // CORS Analysis
    const corsIssues = results.tests.filter(t => t.corsIssue);
    if (corsIssues.length > 0) {
        console.log('\n⚠️  CORS ISSUES DETECTED:');
        corsIssues.forEach(t => {
            console.log(`   - ${t.name}: ${t.error}`);
        });
    }

    // Save results
    const outputDir = path.join(__dirname, '..', 'test_results');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    const outputPath = path.join(outputDir, 'frontend_integration_test.json');
    fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
    console.log(`\n📁 Results saved to: ${outputPath}`);

    return results;
}

// Frontend Component Mapping
const frontendMapping = {
    workstreams: {
        'Workstream 1 - Brand Onboarding': {
            pages: ['OnboardingPage.jsx'],
            components: ['onboarding/OnboardingProgress.jsx', 'onboarding/OnboardingResult.jsx', 'onboarding/OnboardingWelcome.jsx'],
            apiEndpoints: ['/onboarding/start', '/onboarding/status/{id}', '/onboarding/result/{id}']
        },
        'Workstream 2 - Campaign Studio': {
            pages: ['CampaignStudioPage.jsx', 'DashboardPage.jsx'],
            components: ['campaigns/CampaignBrief.jsx', 'campaigns/CampaignCreate.jsx', 'campaigns/CampaignExecution.jsx', 'campaigns/CampaignList.jsx'],
            apiEndpoints: ['/campaigns', '/campaigns/{id}', '/campaigns/{id}/execute']
        },
        'Workstream 3 - AI Chat': {
            pages: ['DashboardPage.jsx (chat view)'],
            components: ['chat/ChatPanel.jsx', 'chat/ChatInput.jsx', 'chat/ChatMessage.jsx'],
            apiEndpoints: ['/chat/conversations', '/chat/conversations/{id}/messages']
        },
        'Workstream 4 - Kata Lab': {
            pages: ['KataLabPage.jsx'],
            components: ['kata/ScriptBuilder.jsx', 'kata/SyntheticInfluencerCreator.jsx', 'kata/VideoCompositor.jsx'],
            apiEndpoints: ['/kata/synthetic-influencer', '/kata/composite-product', '/kata/generate-script', '/kata/halftime/*']
        },
        'Workstream 5 - Asset Generation': {
            pages: ['DashboardPage.jsx (image-editor view)'],
            components: ['image-editor/ConversationalImageEditor.jsx', 'shared/AssetGallery.jsx'],
            apiEndpoints: ['/image-editor/generate', '/image-editor/edit', '/image-editor/sessions']
        },
        'Workstream 6 - Landing Pages': {
            pages: ['DashboardPage.jsx (via component)'],
            components: ['content/LandingPageBuilder.jsx'],
            apiEndpoints: ['/content/landing-page/generate', '/content/landing-page/scaffold']
        },
        'Workstream 7 - Email Marketing': {
            pages: ['DashboardPage.jsx (via component)'],
            components: ['content/EmailBuilder.jsx'],
            apiEndpoints: ['/content/email/generate', '/content/email/subject-variants', '/content/email/templates']
        }
    }
};

// Print frontend mapping
function printFrontendMapping() {
    console.log('\n' + '═'.repeat(60));
    console.log('🗺️  FRONTEND COMPONENT MAPPING');
    console.log('═'.repeat(60));
    
    for (const [workstream, info] of Object.entries(frontendMapping.workstreams)) {
        console.log(`\n${workstream}:`);
        console.log(`  Pages: ${info.pages.join(', ')}`);
        console.log(`  Components: ${info.components.length} components`);
        console.log(`  API Endpoints: ${info.apiEndpoints.length} endpoints`);
    }
}

// Main execution
async function main() {
    try {
        await runTests();
        printFrontendMapping();
        
        console.log('\n' + '═'.repeat(60));
        console.log('✅ Frontend Integration Test Complete');
        console.log('═'.repeat(60));
        
        process.exit(results.summary.failed > 0 ? 1 : 0);
    } catch (error) {
        console.error('❌ Test execution failed:', error);
        process.exit(1);
    }
}

main();
