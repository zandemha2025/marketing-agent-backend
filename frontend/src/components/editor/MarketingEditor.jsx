import React, { useState, useCallback, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import AICommands from './AICommands';
import api from '../../services/api';
import './MarketingEditor.css';

/**
 * Marketing Editor - Jasper-style rich text editor with AI commands
 * 
 * Features:
 * - TipTap editor foundation
 * - Slash commands: /write, /expand, /shorten, /rewrite, /headline, /cta
 * - Brand voice integration
 * - Real-time AI suggestions
 * - 50+ content templates
 */

const CONTENT_TEMPLATES = {
    'blog-intro': {
        name: 'Blog Post Introduction',
        description: 'Hook readers with an engaging opening',
        prompt: 'Write a compelling blog post introduction that hooks the reader and sets up the main topic.'
    },
    'blog-conclusion': {
        name: 'Blog Post Conclusion',
        description: 'Wrap up with a strong call-to-action',
        prompt: 'Write a blog post conclusion that summarizes key points and includes a call-to-action.'
    },
    'linkedin-hook': {
        name: 'LinkedIn Hook',
        description: 'Attention-grabbing opening for LinkedIn',
        prompt: 'Write a LinkedIn post hook (first 2 lines) that stops the scroll.'
    },
    'email-subject': {
        name: 'Email Subject Line',
        description: 'High-converting subject line',
        prompt: 'Write 3 email subject lines that maximize open rates.'
    },
    'product-description': {
        name: 'Product Description',
        description: 'Compelling product copy',
        prompt: 'Write a compelling product description highlighting benefits and features.'
    },
    'value-proposition': {
        name: 'Value Proposition',
        description: 'Clear value statement',
        prompt: 'Write a clear value proposition that explains the unique benefit.'
    },
    'faq': {
        name: 'FAQ Entry',
        description: 'Question and answer format',
        prompt: 'Write a FAQ entry with a common question and helpful answer.'
    },
    'testimonial': {
        name: 'Customer Testimonial',
        description: 'Social proof quote',
        prompt: 'Write a customer testimonial that builds trust and credibility.'
    },
    'case-study-summary': {
        name: 'Case Study Summary',
        description: 'Results-focused summary',
        prompt: 'Write a case study summary highlighting the challenge, solution, and results.'
    },
    'social-proof': {
        name: 'Social Proof Statement',
        description: 'Trust-building statement',
        prompt: 'Write a social proof statement showcasing credibility.'
    },
    'about-us': {
        name: 'About Us Section',
        description: 'Company introduction',
        prompt: 'Write an About Us section that tells the company story.'
    },
    'team-bio': {
        name: 'Team Member Bio',
        description: 'Professional bio',
        prompt: 'Write a professional team member bio.'
    },
    'mission-statement': {
        name: 'Mission Statement',
        description: 'Company mission',
        prompt: 'Write a compelling mission statement.'
    },
    'vision-statement': {
        name: 'Vision Statement',
        description: 'Future vision',
        prompt: 'Write an inspiring vision statement.'
    },
    'cta-button': {
        name: 'CTA Button Text',
        description: 'Action-oriented button copy',
        prompt: 'Write 5 call-to-action button text options.'
    },
    'landing-hero': {
        name: 'Landing Page Hero',
        description: 'Hero section copy',
        prompt: 'Write landing page hero copy with headline and subheadline.'
    },
    'feature-benefit': {
        name: 'Feature + Benefit',
        description: 'Feature with benefit',
        prompt: 'Write a feature description with clear customer benefit.'
    },
    'pricing-tier': {
        name: 'Pricing Tier Description',
        description: 'Pricing plan copy',
        prompt: 'Write a pricing tier description that justifies the value.'
    },
    'comparison': {
        name: 'Comparison Statement',
        description: 'Vs. competitor',
        prompt: 'Write a comparison that highlights advantages without naming competitors.'
    },
    'urgency-scarcity': {
        name: 'Urgency/Scarcity',
        description: 'Create urgency',
        prompt: 'Write copy that creates urgency without being pushy.'
    },
    'guarantee': {
        name: 'Guarantee Statement',
        description: 'Risk reversal',
        prompt: 'Write a guarantee statement that removes purchase risk.'
    },
    'welcome-email': {
        name: 'Welcome Email',
        description: 'Onboarding message',
        prompt: 'Write a welcome email for new customers.'
    },
    'follow-up': {
        name: 'Follow-up Message',
        description: 'Gentle follow-up',
        prompt: 'Write a polite follow-up message.'
    },
    'thank-you': {
        name: 'Thank You Message',
        description: 'Gratitude expression',
        prompt: 'Write a sincere thank you message.'
    },
    'announcement': {
        name: 'Product Announcement',
        description: 'New feature/product',
        prompt: 'Write an exciting product announcement.'
    },
    'update': {
        name: 'Company Update',
        description: 'News/update',
        prompt: 'Write a company update that keeps customers informed.'
    },
    'event-promotion': {
        name: 'Event Promotion',
        description: 'Drive attendance',
        prompt: 'Write copy to promote an upcoming event.'
    },
    'webinar-invite': {
        name: 'Webinar Invitation',
        description: 'Boost registrations',
        prompt: 'Write a webinar invitation that drives registrations.'
    },
    'newsletter-intro': {
        name: 'Newsletter Intro',
        description: 'Engaging opening',
        prompt: 'Write a newsletter introduction that engages readers.'
    },
    'tips-list': {
        name: 'Tips List',
        description: 'Numbered tips',
        prompt: 'Write a list of 5 actionable tips.'
    },
    'how-to': {
        name: 'How-To Guide',
        description: 'Step-by-step',
        prompt: 'Write a how-to guide with clear steps.'
    },
    'checklist': {
        name: 'Checklist',
        description: 'Action items',
        prompt: 'Write a checklist of important items.'
    },
    'definition': {
        name: 'Definition/Explanation',
        description: 'Clear explanation',
        prompt: 'Write a clear definition and explanation of a concept.'
    },
    'myth-fact': {
        name: 'Myth vs Fact',
        description: 'Correct misconceptions',
        prompt: 'Write a myth vs fact comparison.'
    },
    'before-after': {
        name: 'Before/After',
        description: 'Transformation story',
        prompt: 'Write a before and after transformation description.'
    },
    'problem-solution': {
        name: 'Problem-Solution',
        description: 'Address pain point',
        prompt: 'Write a problem-solution format piece.'
    },
    'story-opening': {
        name: 'Story Opening',
        description: 'Narrative hook',
        prompt: 'Write a story opening that draws readers in.'
    },
    'quote-post': {
        name: 'Quote Post',
        description: 'Shareable quote',
        prompt: 'Write an inspiring quote with context.'
    },
    'question-post': {
        name: 'Question Post',
        description: 'Engagement question',
        prompt: 'Write an engaging question that sparks discussion.'
    },
    'poll': {
        name: 'Poll/This or That',
        description: 'Interactive content',
        prompt: 'Write a this-or-that style poll question.'
    },
    'behind-scenes': {
        name: 'Behind the Scenes',
        description: 'Insider look',
        prompt: 'Write a behind-the-scenes description.'
    },
    'user-generated': {
        name: 'UGC Prompt',
        description: 'Encourage sharing',
        prompt: 'Write a prompt encouraging user-generated content.'
    },
    'contest-giveaway': {
        name: 'Contest/Giveaway',
        description: 'Drive participation',
        prompt: 'Write contest or giveaway rules and description.'
    },
    'partnership': {
        name: 'Partnership Announcement',
        description: 'Collaboration news',
        prompt: 'Write a partnership announcement.'
    },
    'award-recognition': {
        name: 'Award Recognition',
        description: 'Celebrate achievement',
        prompt: 'Write an award or recognition announcement.'
    },
    'milestone': {
        name: 'Milestone Celebration',
        description: 'Celebrate progress',
        prompt: 'Write a milestone celebration post.'
    },
    'year-in-review': {
        name: 'Year in Review',
        description: 'Annual recap',
        prompt: 'Write a year in review summary.'
    },
    'predictions': {
        name: 'Industry Predictions',
        description: 'Future trends',
        prompt: 'Write industry predictions for the coming year.'
    },
    'trend-commentary': {
        name: 'Trend Commentary',
        description: 'Thought leadership',
        prompt: 'Write commentary on an industry trend.'
    }
};

const MarketingEditor = ({ 
    organizationId, 
    initialContent = '', 
    onChange,
    placeholder = 'Start typing or type "/" for AI commands...',
    brandVoice = null
}) => {
    const [isProcessing, setIsProcessing] = useState(false);
    const [showTemplates, setShowTemplates] = useState(false);
    const [selectedText, setSelectedText] = useState('');
    const [suggestions, setSuggestions] = useState([]);

    const editor = useEditor({
        extensions: [
            StarterKit,
            Placeholder.configure({
                placeholder,
            }),
        ],
        content: initialContent,
        onUpdate: ({ editor }) => {
            if (onChange) {
                onChange(editor.getHTML(), editor.getText());
            }
        },
        onSelectionUpdate: ({ editor }) => {
            const { from, to } = editor.state.selection;
            if (from !== to) {
                setSelectedText(editor.state.doc.textBetween(from, to));
            } else {
                setSelectedText('');
            }
        },
    });

    // Handle AI commands
    const handleAICommand = useCallback(async (command, params = {}) => {
        if (!editor) return;

        setIsProcessing(true);
        
        try {
            const selectedText = editor.state.doc.textBetween(
                editor.state.selection.from,
                editor.state.selection.to
            );
            
            const context = params.context || selectedText || editor.getText();
            
            let result;
            
            switch (command) {
                case 'write':
                    result = await generateContent('write', context, params.prompt);
                    editor.commands.insertContent(result);
                    break;
                    
                case 'expand':
                    if (!selectedText) {
                        alert('Please select text to expand');
                        return;
                    }
                    result = await generateContent('expand', selectedText);
                    editor.commands.insertContent(result);
                    break;
                    
                case 'shorten':
                    if (!selectedText) {
                        alert('Please select text to shorten');
                        return;
                    }
                    result = await generateContent('shorten', selectedText);
                    editor.commands.deleteSelection();
                    editor.commands.insertContent(result);
                    break;
                    
                case 'rewrite':
                    if (!selectedText) {
                        alert('Please select text to rewrite');
                        return;
                    }
                    result = await generateContent('rewrite', selectedText, params.style);
                    editor.commands.deleteSelection();
                    editor.commands.insertContent(result);
                    break;
                    
                case 'headline':
                    result = await generateContent('headline', context);
                    editor.commands.insertContent(`<h2>${result}</h2>`);
                    break;
                    
                case 'cta':
                    result = await generateContent('cta', context);
                    editor.commands.insertContent(`<p><strong>${result}</strong></p>`);
                    break;
                    
                case 'template':
                    const template = CONTENT_TEMPLATES[params.templateId];
                    if (template) {
                        result = await generateContent('template', context, template.prompt);
                        editor.commands.insertContent(result);
                    }
                    break;
                    
                default:
                    console.warn('Unknown command:', command);
            }
        } catch (error) {
            console.error('AI command failed:', error);
            alert('Failed to process AI command. Please try again.');
        } finally {
            setIsProcessing(false);
        }
    }, [editor, organizationId, brandVoice]);

    const generateContent = async (action, text, additionalPrompt = '') => {
        // This would typically call your backend API
        // For now, we'll simulate with a simple implementation
        
        const voiceGuidelines = brandVoice ? 
            `Use a ${brandVoice.tone?.join(', ')} tone. ${brandVoice.personality}` : '';
        
        const prompts = {
            write: `Write content about: ${text}. ${additionalPrompt} ${voiceGuidelines}`,
            expand: `Expand on this text with more detail and examples: "${text}". ${voiceGuidelines}`,
            shorten: `Shorten this text while keeping the key message: "${text}". Make it concise.`,
            rewrite: `Rewrite this text ${additionalPrompt ? `in a ${additionalPrompt} style` : ''}: "${text}". ${voiceGuidelines}`,
            headline: `Write a compelling headline for this content: "${text}". Keep it under 70 characters.`,
            cta: `Write a call-to-action for this content: "${text}". Make it action-oriented and persuasive.`,
            template: `${additionalPrompt} Context: "${text}". ${voiceGuidelines}`
        };
        
        // FIXME: AI service integration not implemented
        // To implement:
        // 1. Call POST /api/ai/generate with { prompt: prompts[action], organizationId }
        // 2. Return the generated content from the response
        // 3. Handle errors appropriately
        console.warn(`AI ${action} command not implemented - backend integration required`);
        throw new Error(
            `AI content generation is not yet connected to the backend. ` +
            `Action: "${action}". Please use the Campaign Studio for AI-powered content.`
        );
    };

    const insertTemplate = (templateId) => {
        const template = CONTENT_TEMPLATES[templateId];
        if (template && editor) {
            handleAICommand('template', { templateId, prompt: template.prompt });
            setShowTemplates(false);
        }
    };

    if (!editor) {
        return <div className="marketing-editor loading">Loading editor...</div>;
    }

    return (
        <div className="marketing-editor">
            {/* Toolbar */}
            <div className="editor-toolbar">
                <div className="toolbar-section formatting">
                    <button
                        onClick={() => editor.chain().focus().toggleBold().run()}
                        className={editor.isActive('bold') ? 'active' : ''}
                        title="Bold"
                    >
                        <strong>B</strong>
                    </button>
                    <button
                        onClick={() => editor.chain().focus().toggleItalic().run()}
                        className={editor.isActive('italic') ? 'active' : ''}
                        title="Italic"
                    >
                        <em>I</em>
                    </button>
                    <button
                        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                        className={editor.isActive('heading', { level: 2 }) ? 'active' : ''}
                        title="Heading"
                    >
                        H2
                    </button>
                    <button
                        onClick={() => editor.chain().focus().toggleBulletList().run()}
                        className={editor.isActive('bulletList') ? 'active' : ''}
                        title="Bullet List"
                    >
                        • List
                    </button>
                    <button
                        onClick={() => editor.chain().focus().toggleOrderedList().run()}
                        className={editor.isActive('orderedList') ? 'active' : ''}
                        title="Numbered List"
                    >
                        1. List
                    </button>
                </div>

                <div className="toolbar-section ai-commands">
                    <AICommands 
                        editor={editor} 
                        onCommand={handleAICommand}
                        isProcessing={isProcessing}
                    />
                </div>

                <div className="toolbar-section templates">
                    <button 
                        className="template-btn"
                        onClick={() => setShowTemplates(!showTemplates)}
                    >
                        📋 Templates
                    </button>
                </div>
            </div>

            {/* Template Panel */}
            {showTemplates && (
                <div className="template-panel">
                    <div className="template-header">
                        <h4>Content Templates</h4>
                        <button onClick={() => setShowTemplates(false)}>✕</button>
                    </div>
                    <div className="template-grid">
                        {Object.entries(CONTENT_TEMPLATES).map(([id, template]) => (
                            <button
                                key={id}
                                className="template-item"
                                onClick={() => insertTemplate(id)}
                            >
                                <span className="template-name">{template.name}</span>
                                <span className="template-desc">{template.description}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Editor Content */}
            <div className="editor-content-wrapper">
                <EditorContent editor={editor} className="editor-content" />
                
                {isProcessing && (
                    <div className="processing-overlay">
                        <div className="spinner"></div>
                        <span>AI is working...</span>
                    </div>
                )}
            </div>

            {/* Status Bar */}
            <div className="editor-status">
                <span>{editor.storage.characterCount?.characters?.() || editor.getText().length} characters</span>
                <span>{editor.getText().split(/\s+/).filter(w => w).length} words</span>
                {selectedText && <span className="selected-indicator">{selectedText.length} selected</span>}
            </div>
        </div>
    );
};

export default MarketingEditor;