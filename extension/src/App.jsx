import React, { useState, useEffect, useCallback, useRef } from 'react';
import CommandBar from './components/CommandBar.jsx';
import ActionFeed from './components/ActionFeed.jsx';

const BACKEND_WS_URL = 'ws://localhost:8000/ws/';

/**
 * Pilot — Root Application
 *
 * The side panel manages the WebSocket connection directly (not the service
 * worker), because Manifest V3 service workers have restrictions on
 * long-lived WebSocket connections.
 */
export default function App() {
    const [isConnected, setIsConnected] = useState(false);
    const [status, setStatus] = useState('idle');
    const [statusMessage, setStatusMessage] = useState('');
    const [steps, setSteps] = useState([]);
    const [plan, setPlan] = useState(null);
    const [connectionDetail, setConnectionDetail] = useState('Initializing...');
    const wsRef = useRef(null);
    const sessionIdRef = useRef(crypto.randomUUID());

    // ---------------------------------------------------------------------------
    // WebSocket connection (managed directly from the side panel)
    // ---------------------------------------------------------------------------
    const connectToBackend = useCallback(() => {
        // Close existing
        if (wsRef.current) {
            try { wsRef.current.close(); } catch (e) { /* ignore */ }
        }

        const url = BACKEND_WS_URL + sessionIdRef.current;
        console.log('[Pilot] Connecting to:', url);
        setConnectionDetail('Connecting to ' + url + '...');

        let ws;
        try {
            ws = new WebSocket(url);
        } catch (err) {
            console.error('[Pilot] WebSocket constructor error:', err);
            setConnectionDetail('Failed to create WebSocket: ' + err.message);
            return;
        }

        ws.onopen = () => {
            console.log('[Pilot] WebSocket OPEN');
            setIsConnected(true);
            setConnectionDetail('Connected to backend');
            wsRef.current = ws;
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('[Pilot] Message:', data.type, data);
            handleBackendMessage(data);
        };

        ws.onclose = (event) => {
            console.log('[Pilot] WebSocket CLOSED, code:', event.code);
            setIsConnected(false);
            setConnectionDetail(`Disconnected (code: ${event.code}). Click Retry.`);
            wsRef.current = null;
        };

        ws.onerror = (err) => {
            console.error('[Pilot] WebSocket ERROR:', err);
            setConnectionDetail('Connection failed. Is backend running on localhost:8000?');
        };

        wsRef.current = ws;
    }, []);

    // ---------------------------------------------------------------------------
    // Handle backend messages
    // ---------------------------------------------------------------------------
    const handleBackendMessage = useCallback((data) => {
        switch (data.type) {
            case 'connected':
                setStatusMessage(data.message || 'Ready');
                break;

            case 'request_screenshot':
                captureAndSendScreenshot();
                break;

            case 'execute_action':
                executeActionViaBackground(data.action, data.step_index, data.step_description);
                break;

            case 'status':
                setStatus(data.status);
                setStatusMessage(data.message || '');
                break;

            case 'plan':
                setPlan({
                    steps: data.steps || [],
                    reasoning: data.reasoning || '',
                    confidence: data.confidence || 0,
                });
                break;

            case 'narration':
                setSteps((prev) => {
                    const existing = prev.findIndex(
                        (s) => s.step === data.step && s.status === 'running'
                    );
                    if (existing >= 0) {
                        const updated = [...prev];
                        updated[existing] = {
                            ...updated[existing],
                            message: data.message,
                            status: data.status,
                        };
                        return updated;
                    }
                    return [...prev, {
                        step: data.step,
                        message: data.message,
                        status: data.status,
                        meta: data.meta || null,
                    }];
                });
                break;

            case 'error':
                setStatusMessage(data.message || 'An error occurred');
                break;
        }
    }, []);

    // ---------------------------------------------------------------------------
    // Screenshot capture — ask background worker to capture
    // ---------------------------------------------------------------------------
    const captureAndSendScreenshot = useCallback(() => {
        console.log('[Pilot] Requesting screenshot from background...');
        chrome.runtime.sendMessage({ type: 'capture_screenshot' }, (response) => {
            if (response && response.image) {
                console.log('[Pilot] Screenshot received, size:', response.image.length);
                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({
                        type: 'screenshot',
                        image: response.image,
                        tabId: response.tabId,
                        url: response.url,
                    }));
                }
            } else {
                console.error('[Pilot] Screenshot capture failed:', response);
            }
        });
    }, []);

    // ---------------------------------------------------------------------------
    // Execute actions — ask background to use chrome.debugger
    // ---------------------------------------------------------------------------
    const executeActionViaBackground = useCallback((action, stepIndex, stepDescription) => {
        console.log('[Pilot] Sending action to background:', action.type);
        chrome.runtime.sendMessage({
            type: 'execute_action',
            action,
            step_index: stepIndex,
        }, (response) => {
            console.log('[Pilot] Action execution response:', response);
        });
    }, []);

    // ---------------------------------------------------------------------------
    // Connect on mount
    // ---------------------------------------------------------------------------
    useEffect(() => {
        connectToBackend();

        // Listen for action results from background
        const listener = (message) => {
            if (message.type === 'action_executed') {
                console.log('[Pilot] Action executed by background:', message);
            } else if (message.type === 'error') {
                setStatusMessage(message.message || 'Error');
            }
        };
        chrome.runtime.onMessage.addListener(listener);

        return () => {
            chrome.runtime.onMessage.removeListener(listener);
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connectToBackend]);

    // ---------------------------------------------------------------------------
    // Actions
    // ---------------------------------------------------------------------------
    const handleSubmitGoal = (goal) => {
        setSteps([]);
        setPlan(null);
        setStatus('planning');
        setStatusMessage(`Planning: ${goal}`);
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'goal', goal }));
        }
    };

    const handleStop = () => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'stop' }));
        }
        setStatus('idle');
        setStatusMessage('Stopped');
    };

    const handlePause = () => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pause' }));
        }
    };

    const handleResume = () => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'resume' }));
        }
    };

    const handleRetryConnect = () => {
        sessionIdRef.current = crypto.randomUUID();
        connectToBackend();
    };

    // ---------------------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------------------
    const statusClass =
        status === 'completed' ? 'completed' :
            status === 'failed' ? 'failed' :
                status === 'planning' ? 'planning' :
                    (status === 'executing' || status === 'verifying') ? 'executing' : '';

    return (
        <>
            <header className="pilot-header">
                <div className="pilot-logo">
                    <div className="pilot-logo-icon">P</div>
                    <span className="pilot-logo-text">Pilot</span>
                </div>
                <div
                    className={`connection-dot ${isConnected ? 'connected' : ''}`}
                    title={isConnected ? 'Connected' : 'Disconnected'}
                />
            </header>

            <div className={`connection-banner ${isConnected ? 'connected' : 'disconnected'}`}>
                <div className="connection-banner-dot" />
                <span className="connection-banner-text">
                    {isConnected ? 'API Connected' : connectionDetail}
                </span>
                {!isConnected && (
                    <button className="connection-retry-btn" onClick={handleRetryConnect}>
                        Retry
                    </button>
                )}
            </div>

            <CommandBar
                onSubmit={handleSubmitGoal}
                onStop={handleStop}
                onPause={handlePause}
                onResume={handleResume}
                status={status}
                isConnected={isConnected}
            />

            {statusMessage && status !== 'idle' && (
                <div className={`status-banner ${statusClass}`}>
                    {(status === 'planning' || status === 'executing' || status === 'verifying') && (
                        <div className="status-spinner" />
                    )}
                    {statusMessage}
                </div>
            )}

            <ActionFeed steps={steps} plan={plan} status={status} />
        </>
    );
}
