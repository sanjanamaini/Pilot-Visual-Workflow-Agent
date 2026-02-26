import React, { useState, useRef } from 'react';

/**
 * CommandBar — Floating command input with voice support and workflow controls.
 */
export default function CommandBar({ onSubmit, onStop, onPause, onResume, status, isConnected }) {
    const [goal, setGoal] = useState('');
    const textareaRef = useRef(null);

    const isExecuting = status === 'executing' || status === 'planning' || status === 'verifying';
    const isPaused = status === 'paused';

    const handleSubmit = () => {
        const trimmed = goal.trim();
        if (!trimmed || !isConnected || isExecuting) return;
        onSubmit(trimmed);
        setGoal('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    // Auto-resize textarea
    const handleInput = (e) => {
        setGoal(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
    };

    return (
        <div className="command-bar">
            <div className="command-input-wrapper">
                <textarea
                    ref={textareaRef}
                    className="command-input"
                    placeholder={isConnected ? "Tell Pilot what to do..." : "Connecting..."}
                    value={goal}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                    disabled={!isConnected || isExecuting}
                    rows={1}
                />
                <button
                    className="command-submit"
                    onClick={handleSubmit}
                    disabled={!goal.trim() || !isConnected || isExecuting}
                    title="Send command"
                >
                    ▶
                </button>
            </div>

            {isExecuting && (
                <div className="controls-bar fade-in">
                    <button className="control-btn" onClick={onPause}>
                        ⏸ Pause
                    </button>
                    <button className="control-btn stop" onClick={onStop}>
                        ⏹ Stop
                    </button>
                </div>
            )}

            {isPaused && (
                <div className="controls-bar fade-in">
                    <button className="control-btn" onClick={onResume}>
                        ▶ Resume
                    </button>
                    <button className="control-btn stop" onClick={onStop}>
                        ⏹ Stop
                    </button>
                </div>
            )}
        </div>
    );
}
