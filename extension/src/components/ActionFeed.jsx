import React, { useEffect, useRef } from 'react';

/**
 * ActionFeed — Live narration sidebar showing each agent step.
 */

const STATUS_ICONS = {
    running: '⟳',
    done: '✓',
    failed: '✗',
    pending: '○',
};

function StepCard({ step }) {
    const statusClass = step.status || 'pending';
    return (
        <div className="step-card">
            <div className={`step-icon ${statusClass}`}>
                {STATUS_ICONS[statusClass] || '○'}
            </div>
            <div className="step-content">
                <div className="step-label">{step.message}</div>
                {step.meta && <div className="step-meta">{step.meta}</div>}
            </div>
        </div>
    );
}

function PlanSection({ plan }) {
    if (!plan || !plan.steps || plan.steps.length === 0) return null;

    return (
        <div className="plan-section">
            <div className="plan-header">
                📋 Action Plan
            </div>
            <ol className="plan-steps">
                {plan.steps.map((step, i) => (
                    <li key={i} className="plan-step">
                        <span className="plan-step-number">{i + 1}</span>
                        <span>{step}</span>
                    </li>
                ))}
            </ol>
            {plan.reasoning && (
                <div className="step-meta" style={{ marginTop: '8px' }}>
                    💡 {plan.reasoning}
                </div>
            )}
        </div>
    );
}

export default function ActionFeed({ steps, plan, status }) {
    const feedRef = useRef(null);

    // Auto-scroll to bottom on new steps
    useEffect(() => {
        if (feedRef.current) {
            feedRef.current.scrollTop = feedRef.current.scrollHeight;
        }
    }, [steps.length]);

    const isEmpty = steps.length === 0 && !plan;

    return (
        <div className="action-feed" ref={feedRef}>
            {isEmpty && (
                <div className="feed-empty">
                    <div className="feed-empty-icon">🧭</div>
                    <div className="feed-empty-title">Ready to navigate</div>
                    <div className="feed-empty-desc">
                        Tell Pilot what you want to accomplish. It will watch your screen and act across any web app — no setup required.
                    </div>
                </div>
            )}

            {plan && <PlanSection plan={plan} />}

            {steps.map((step, i) => (
                <StepCard key={`${step.step}-${i}`} step={step} />
            ))}
        </div>
    );
}
