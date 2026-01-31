
// Mock API
const api = {
    getOnboardingStatus: async (orgId) => {
        console.log(`API: getOnboardingStatus called for ${orgId}`);
        // Simulate network delay
        await new Promise(r => setTimeout(r, 100));
        
        // Return completed status immediately for testing (or after a few calls)
        return {
            status: 'complete',
            progress: {
                stage: 'complete',
                progress: 1.0,
                message: 'All done'
            }
        };
    },
    getOnboardingResult: async (orgId) => {
        console.log(`API: getOnboardingResult called for ${orgId}`);
        return { data: 'Result Data' };
    }
};

// Mock State
let stage = 'welcome';
let progress = { stage: 'initializing', progress: 0, message: 'Preparing...' };
let result = null;

const setStage = (newStage) => {
    console.log(`STATE: setStage -> ${newStage}`);
    stage = newStage;
};

const setProgress = (newProgress) => {
    console.log(`STATE: setProgress -> ${JSON.stringify(newProgress)}`);
    progress = newProgress;
};

const setResult = (newResult) => {
    console.log(`STATE: setResult -> ${JSON.stringify(newResult)}`);
    result = newResult;
};

// Logic from OnboardingPage.jsx (simplified for standalone execution)

// Mocking useCallback by just defining the function.
// NOTE: In the real component, this is inside the component function.
// The critical part is the recursion: pollStatus calls pollStatus.

const pollStatus = async (orgId) => {
    try {
        console.log('POLL: Starting poll iteration...');
        const status = await api.getOnboardingStatus(orgId);

        setProgress({
            stage: status.progress.stage,
            progress: status.progress.progress,
            message: status.progress.message,
        });

        if (status.status === 'complete') {
            console.log('POLL: Status is complete. Fetching result...');
             // This is the critical block that supposedly fails to update UI
            const resultData = await api.getOnboardingResult(orgId);
            setResult(resultData);
            setStage('result');
            console.log('POLL: Finished completion flow.');
        } else if (status.status === 'failed') {
            // ...
        } else {
            // Keep polling
            console.log('POLL: Not complete, scheduling next poll...');
            setTimeout(() => pollStatus(orgId), 2000);
        }
    } catch (err) {
        console.error('POLL ERROR:', err);
    }
};

// Execute
console.log('SCRIPT: Starting simulation...');
pollStatus('org-123');

// Keep process alive for a bit to allow async operations
setTimeout(() => {
    console.log('SCRIPT: End of simulation time.');
}, 3000);
