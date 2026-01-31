import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Extension } from '@tiptap/core';
import Suggestion from '@tiptap/suggestion';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';
import './AICommands.css';

/**
 * AI Commands Component - Slash command system for the Marketing Editor
 * 
 * Commands:
 * - /write - Generate new content
 * - /expand - Expand selected text
 * - /shorten - Condense selected text
 * - /rewrite - Rewrite in different style
 * - /headline - Generate headline
 * - /cta - Generate call-to-action
 */

const COMMANDS = [
    {
        name: 'write',
        label: 'Write',
        description: 'Generate new content',
        icon: '✍️',
        shortcut: 'Type a topic or prompt',
    },
    {
        name: 'expand',
        label: 'Expand',
        description: 'Add more detail to selected text',
        icon: '↔️',
        shortcut: 'Select text first',
    },
    {
        name: 'shorten',
        label: 'Shorten',
        description: 'Make selected text more concise',
        icon: '➡️',
        shortcut: 'Select text first',
    },
    {
        name: 'rewrite',
        label: 'Rewrite',
        description: 'Rewrite in different style',
        icon: '🔄',
        shortcut: 'Select text first',
        options: ['professional', 'casual', 'enthusiastic', 'formal', 'simple']
    },
    {
        name: 'headline',
        label: 'Headline',
        description: 'Generate attention-grabbing headline',
        icon: '📰',
        shortcut: 'Based on content',
    },
    {
        name: 'cta',
        label: 'CTA',
        description: 'Generate call-to-action',
        icon: '👉',
        shortcut: 'Based on content',
    },
    {
        name: 'improve',
        label: 'Improve',
        description: 'Enhance writing quality',
        icon: '✨',
        shortcut: 'Select text first',
    },
    {
        name: 'fix',
        label: 'Fix Grammar',
        description: 'Fix grammar and spelling',
        icon: '🔧',
        shortcut: 'Select text first',
    },
];

// Suggestion plugin configuration
const AICommandSuggestion = {
    items: ({ query }) => {
        return COMMANDS.filter(command =>
            command.name.toLowerCase().includes(query.toLowerCase()) ||
            command.label.toLowerCase().includes(query.toLowerCase()) ||
            command.description.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 10);
    },

    render: () => {
        let component;
        let popup;

        return {
            onStart: props => {
                component = document.createElement('div');
                component.className = 'ai-command-menu';
                
                popup = tippy('body', {
                    getReferenceClientRect: props.clientRect,
                    appendTo: () => document.body,
                    content: component,
                    showOnCreate: true,
                    interactive: true,
                    trigger: 'manual',
                    placement: 'bottom-start',
                    offset: [0, 8],
                    popperOptions: {
                        strategy: 'fixed',
                    },
                })[0];

                // Render initial items
                renderCommandMenu(component, props);
            },

            onUpdate: props => {
                if (popup) {
                    popup.setProps({
                        getReferenceClientRect: props.clientRect,
                    });
                }
                renderCommandMenu(component, props);
            },

            onKeyDown: props => {
                if (props.event.key === 'Escape') {
                    popup?.hide();
                    return true;
                }
                return false;
            },

            onExit: () => {
                popup?.destroy();
                component?.remove();
            },
        };
    },
};

function renderCommandMenu(container, props) {
    const { items, command } = props;
    
    container.innerHTML = '';
    
    if (items.length === 0) {
        container.innerHTML = '<div class="command-empty">No commands found</div>';
        return;
    }

    const list = document.createElement('div');
    list.className = 'command-list';
    
    items.forEach((item, index) => {
        const button = document.createElement('button');
        button.className = `command-item ${index === props.selectedIndex ? 'selected' : ''}`;
        button.innerHTML = `
            <span class="command-icon">${item.icon}</span>
            <div class="command-info">
                <span class="command-label">${item.label}</span>
                <span class="command-description">${item.description}</span>
            </div>
            <span class="command-shortcut">${item.shortcut}</span>
        `;
        button.onclick = () => command(item);
        list.appendChild(button);
    });
    
    container.appendChild(list);
}

// Create the extension
export const AICommandExtension = Extension.create({
    name: 'aiCommands',

    addOptions() {
        return {
            suggestion: {
                char: '/',
                command: ({ editor, range, props }) => {
                    props.command({ editor, range, props });
                },
            },
        };
    },

    addProseMirrorPlugins() {
        return [
            Suggestion({
                editor: this.editor,
                ...this.options.suggestion,
                ...AICommandSuggestion,
            }),
        ];
    },
});

// React Component for the command palette
const AICommands = ({ editor, onCommand, isProcessing }) => {
    const [showPalette, setShowPalette] = useState(false);
    const [selectedCommand, setSelectedCommand] = useState(null);
    const [commandInput, setCommandInput] = useState('');
    const [selectedStyle, setSelectedStyle] = useState('professional');
    const paletteRef = useRef(null);

    // Handle slash key to show palette
    useEffect(() => {
        if (!editor) return;

        const handleKeyDown = (event) => {
            if (event.key === '/' && !showPalette) {
                // Check if we're at the start of a line or after a space
                const { from } = editor.state.selection;
                const textBefore = editor.state.doc.textBetween(Math.max(0, from - 1), from);
                
                if (textBefore === '' || textBefore === ' ' || textBefore === '\n') {
                    setShowPalette(true);
                    setSelectedCommand(null);
                    setCommandInput('');
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [editor, showPalette]);

    // Close palette on click outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (paletteRef.current && !paletteRef.current.contains(event.target)) {
                setShowPalette(false);
            }
        };

        if (showPalette) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [showPalette]);

    const executeCommand = useCallback((command) => {
        if (!editor) return;

        // Remove the slash character
        const { from } = editor.state.selection;
        editor.commands.deleteRange({ from: from - 1, to: from });

        if (command.name === 'rewrite') {
            setSelectedCommand(command);
        } else if (command.name === 'write') {
            setSelectedCommand(command);
        } else {
            onCommand(command.name);
            setShowPalette(false);
        }
    }, [editor, onCommand]);

    const handleSubmitCommand = () => {
        if (selectedCommand && commandInput) {
            onCommand(selectedCommand.name, { 
                prompt: commandInput,
                style: selectedCommand.name === 'rewrite' ? selectedStyle : undefined
            });
            setShowPalette(false);
            setCommandInput('');
            setSelectedCommand(null);
        }
    };

    const filteredCommands = COMMANDS.filter(cmd =>
        cmd.name.toLowerCase().includes(commandInput.toLowerCase()) ||
        cmd.label.toLowerCase().includes(commandInput.toLowerCase())
    );

    if (!showPalette) {
        return (
            <div className="ai-commands-trigger">
                <button 
                    className="slash-command-btn"
                    onClick={() => setShowPalette(true)}
                    title="Press / for AI commands"
                >
                    ✨ AI
                </button>
            </div>
        );
    }

    return (
        <div className="ai-commands-palette" ref={paletteRef}>
            {!selectedCommand ? (
                <>
                    <div className="palette-header">
                        <input
                            type="text"
                            placeholder="Type a command or search..."
                            value={commandInput}
                            onChange={(e) => setCommandInput(e.target.value)}
                            autoFocus
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && filteredCommands.length > 0) {
                                    executeCommand(filteredCommands[0]);
                                }
                                if (e.key === 'Escape') {
                                    setShowPalette(false);
                                }
                            }}
                        />
                        <button onClick={() => setShowPalette(false)}>✕</button>
                    </div>
                    
                    <div className="palette-commands">
                        {filteredCommands.map((command) => (
                            <button
                                key={command.name}
                                className="palette-command"
                                onClick={() => executeCommand(command)}
                            >
                                <span className="command-icon">{command.icon}</span>
                                <div className="command-details">
                                    <span className="command-name">{command.label}</span>
                                    <span className="command-desc">{command.description}</span>
                                </div>
                                <span className="command-hint">{command.shortcut}</span>
                            </button>
                        ))}
                    </div>
                    
                    <div className="palette-footer">
                        <span>Press <kbd>↑</kbd> <kbd>↓</kbd> to navigate, <kbd>Enter</kbd> to select</span>
                    </div>
                </>
            ) : (
                <div className="command-input-panel">
                    <div className="input-header">
                        <span className="input-icon">{selectedCommand.icon}</span>
                        <span className="input-label">{selectedCommand.label}</span>
                    </div>
                    
                    {selectedCommand.name === 'rewrite' && (
                        <div className="style-selector">
                            <label>Style:</label>
                            <select 
                                value={selectedStyle}
                                onChange={(e) => setSelectedStyle(e.target.value)}
                            >
                                {selectedCommand.options.map(style => (
                                    <option key={style} value={style}>
                                        {style.charAt(0).toUpperCase() + style.slice(1)}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                    
                    <textarea
                        placeholder={
                            selectedCommand.name === 'write' 
                                ? "What would you like me to write about?"
                                : "Any specific instructions? (optional)"
                        }
                        value={commandInput}
                        onChange={(e) => setCommandInput(e.target.value)}
                        rows={3}
                        autoFocus
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && e.metaKey) {
                                handleSubmitCommand();
                            }
                            if (e.key === 'Escape') {
                                setSelectedCommand(null);
                            }
                        }}
                    />
                    
                    <div className="input-actions">
                        <button onClick={() => setSelectedCommand(null)}>← Back</button>
                        <button 
                            className="primary"
                            onClick={handleSubmitCommand}
                            disabled={!commandInput.trim() || isProcessing}
                        >
                            {isProcessing ? 'Processing...' : 'Generate'}
                        </button>
                    </div>
                    
                    <div className="input-hint">
                        Press <kbd>Cmd</kbd> + <kbd>Enter</kbd> to generate
                    </div>
                </div>
            )}
        </div>
    );
};

export default AICommands;