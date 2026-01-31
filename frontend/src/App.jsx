import React, { useState, useEffect } from 'react';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import KataLabPage from './pages/KataLabPage';
import LoginPage from './pages/LoginPage';
import TrendMasterPage from './pages/TrendMasterPage';
import ArticleWriterPage from './pages/ArticleWriterPage';
import KanbanPage from './pages/KanbanPage';
import CalendarPage from './pages/CalendarPage';
import api from './services/api';
import './styles/global.css';

function App() {
    const [currentPage, setCurrentPage] = useState('loading');
    const [organizationId, setOrganizationId] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Check auth status on mount
    useEffect(() => {
        const checkAuth = async () => {
            const token = api.getAuthToken();
            const storedOrgId = localStorage.getItem('organizationId');

            if (token) {
                try {
                    // Verify token is valid by fetching user
                    const user = await api.getMe();
                    setIsAuthenticated(true);
                    if (user?.organization_id) {
                        setOrganizationId(user.organization_id);
                        localStorage.setItem('organizationId', user.organization_id);
                    } else if (storedOrgId) {
                        setOrganizationId(storedOrgId);
                    }
                    setCurrentPage('dashboard');
                } catch (err) {
                    // Token invalid, clear it
                    api.logout();
                    setIsAuthenticated(false);
                    setCurrentPage('login');
                }
            } else if (storedOrgId) {
                // Legacy: has org but no auth token - require login
                // Clear the stale org ID and redirect to login
                localStorage.removeItem('organizationId');
                setCurrentPage('login');
            } else {
                setCurrentPage('login');
            }
        };

        checkAuth();
    }, []);

    const handleLoginSuccess = async (orgId, isNewUser = false) => {
        setOrganizationId(orgId);
        setIsAuthenticated(true);

        // New users always go to onboarding
        if (isNewUser) {
            setCurrentPage('onboarding');
            return;
        }

        // Existing users: check if they have completed onboarding (have brand data)
        try {
            const kb = await api.getKnowledgeBase(orgId);
            const hasCompletedOnboarding = kb?.brand_data?.name || kb?.brand_data?.domain;
            setCurrentPage(hasCompletedOnboarding ? 'dashboard' : 'onboarding');
        } catch (err) {
            // If can't check, assume onboarding needed for safety
            console.warn('Could not check onboarding status:', err);
            setCurrentPage('onboarding');
        }
    };

    const handleOnboardingComplete = (orgId) => {
        setOrganizationId(orgId);
        localStorage.setItem('organizationId', orgId);
        setCurrentPage('dashboard');
    };

    const handleLogout = () => {
        api.logout();
        setIsAuthenticated(false);
        setOrganizationId(null);
        setCurrentPage('login');
    };

    const navigateTo = (page) => {
        setCurrentPage(page);
    };

    // Loading state
    if (currentPage === 'loading') {
        return (
            <div className="app loading">
                <div className="loading-spinner">Loading...</div>
            </div>
        );
    }

    return (
        <div className="app">
            {currentPage === 'login' && (
                <LoginPage onLoginSuccess={handleLoginSuccess} />
            )}
            {currentPage === 'onboarding' && (
                <OnboardingPage onComplete={handleOnboardingComplete} />
            )}
            {currentPage === 'dashboard' && organizationId && (
                <DashboardPage
                    organizationId={organizationId}
                    onLogout={handleLogout}
                    onNavigate={navigateTo}
                />
            )}
            {currentPage === 'kata-lab' && organizationId && (
                <KataLabPage
                    organizationId={organizationId}
                    onBack={() => navigateTo('dashboard')}
                />
            )}
            {currentPage === 'trendmaster' && organizationId && (
                <TrendMasterPage
                    organizationId={organizationId}
                    onBack={() => navigateTo('dashboard')}
                />
            )}
            {currentPage === 'article-writer' && organizationId && (
                <ArticleWriterPage
                    organizationId={organizationId}
                    onBack={() => navigateTo('dashboard')}
                />
            )}
            {currentPage === 'kanban' && organizationId && (
                <KanbanPage organizationId={organizationId} />
            )}
            {currentPage === 'calendar' && organizationId && (
                <CalendarPage organizationId={organizationId} />
            )}
        </div>
    );
}

export default App;
