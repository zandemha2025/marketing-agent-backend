import React, { useState } from 'react';
import { Eye, EyeOff, Loader2, Check, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { useToast } from '../components/Toast';
import './LoginPage.css';

function LoginPage({ onLoginSuccess }) {
    const { addToast } = useToast();
    const [isLogin, setIsLogin] = useState(true);
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        name: '',
        organizationName: '',
    });
    const [errors, setErrors] = useState({});

    const validateForm = () => {
        const newErrors = {};

        if (!formData.email || !formData.email.includes('@')) {
            newErrors.email = 'Please enter a valid email';
        }

        if (!formData.password || formData.password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters';
        }

        if (!isLogin && !formData.name.trim()) {
            newErrors.name = 'Name is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        setLoading(true);

        try {
            let response;
            if (isLogin) {
                response = await api.login(formData.email, formData.password);
                addToast('Welcome back!', 'success');
            } else {
                response = await api.register(
                    formData.email,
                    formData.password,
                    formData.name,
                    formData.organizationName
                );
                addToast('Account created successfully!', 'success');
            }

            if (response.user?.organization_id) {
                // Pass isNewUser=true for registration, false for login
                onLoginSuccess(response.user.organization_id, !isLogin);
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (err) {
            console.error('Auth error:', err);
            const message = err.message || 'Authentication failed. Please try again.';
            addToast(message, 'error');
            setErrors(prev => ({ ...prev, form: message }));
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: undefined }));
        }
    };

    return (
        <div className="login-page">
            <div className={`login-card ${errors.form ? 'shake' : ''}`}>
                <div className="login-header">
                    <div className="brand-logo">✨</div>
                    <h1>{isLogin ? 'Welcome back' : 'Create your account'}</h1>
                    <p className="subtitle">
                        {isLogin
                            ? 'Sign in to your account to continue'
                            : 'Start your 14-day free trial'}
                    </p>
                </div>

                <div className="sso-buttons">
                    <button type="button" className="btn btn-secondary btn-full sso-btn">
                        Continue with Google
                    </button>
                    <button type="button" className="btn btn-secondary btn-full sso-btn">
                        Continue with Microsoft
                    </button>
                </div>

                <div className="divider">
                    <span>or</span>
                </div>

                <form className="login-form" onSubmit={handleSubmit}>
                    {!isLogin && (
                        <div className="form-group">
                            <label htmlFor="name">Full Name</label>
                            <input
                                type="text"
                                id="name"
                                name="name"
                                value={formData.name}
                                onChange={handleChange}
                                placeholder="John Doe"
                                disabled={loading}
                                className={errors.name ? 'error' : ''}
                            />
                            {errors.name && <span className="error-message">{errors.name}</span>}
                        </div>
                    )}

                    <div className="form-group">
                        <label htmlFor="email">Email address</label>
                        <input
                            type="email"
                            id="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="you@company.com"
                            disabled={loading}
                            className={errors.email ? 'error' : ''}
                        />
                        {errors.email && <span className="error-message">{errors.email}</span>}
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <div className="password-input-wrapper">
                            <input
                                type={showPassword ? 'text' : 'password'}
                                id="password"
                                name="password"
                                value={formData.password}
                                onChange={handleChange}
                                placeholder="••••••••"
                                disabled={loading}
                                className={errors.password ? 'error' : ''}
                            />
                            <button
                                type="button"
                                className="password-toggle"
                                onClick={() => setShowPassword(!showPassword)}
                                tabIndex="-1"
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                        {errors.password && <span className="error-message">{errors.password}</span>}
                    </div>

                    {isLogin ? (
                        <div className="form-actions">
                            <a href="#" className="forgot-password" onClick={(e) => { e.preventDefault(); addToast('Not implemented', 'info'); }}>
                                Forgot password?
                            </a>
                        </div>
                    ) : (
                        <div className="form-group">
                            <label htmlFor="organizationName">
                                Organization Name <span className="optional">(optional)</span>
                            </label>
                            <input
                                type="text"
                                id="organizationName"
                                name="organizationName"
                                value={formData.organizationName}
                                onChange={handleChange}
                                placeholder="Acme Inc."
                                disabled={loading}
                            />
                        </div>
                    )}

                    {!isLogin && (
                        <div className="terms-check">
                            <input type="checkbox" id="terms" required />
                            <label htmlFor="terms">
                                I agree to the <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>
                            </label>
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary btn-full submit-btn"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <Loader2 size={18} className="animate-spin" />
                                {isLogin ? 'Signing in...' : 'Creating account...'}
                            </>
                        ) : (
                            isLogin ? 'Sign in' : 'Create account'
                        )}
                    </button>
                </form>

                <div className="login-footer">
                    <p>
                        {isLogin ? "Don't have an account? " : "Already have an account? "}
                        <button
                            type="button"
                            className="link-button"
                            onClick={() => {
                                setIsLogin(!isLogin);
                                setErrors({});
                            }}
                            disabled={loading}
                        >
                            {isLogin ? 'Sign up' : 'Sign in'}
                        </button>
                    </p>
                </div>
            </div>
        </div>
    );
}

export default LoginPage;
