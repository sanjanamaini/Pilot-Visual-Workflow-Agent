/**
 * Pilot — Background Service Worker
 *
 * Handles screenshot capture and action execution (which require chrome.tabs
 * and chrome.debugger APIs). The WebSocket connection is managed by the
 * side panel directly.
 */

let attachedTabId = null;

// ---------------------------------------------------------------------------
// Message listener
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('[Pilot BG] Message:', message.type);

    switch (message.type) {
        case 'capture_screenshot':
            captureScreenshot().then((result) => {
                sendResponse(result);
            }).catch((err) => {
                console.error('[Pilot BG] Screenshot error:', err);
                sendResponse({ error: err.message });
            });
            return true; // Keep channel open for async response

        case 'execute_action':
            executeAction(message.action, message.step_index).then(() => {
                sendResponse({ ok: true });
            }).catch((err) => {
                console.error('[Pilot BG] Action error:', err);
                sendResponse({ error: err.message });
            });
            return true;
    }
});

// ---------------------------------------------------------------------------
// Screenshot capture
// ---------------------------------------------------------------------------

async function captureScreenshot() {
    console.log('[Pilot BG] Capturing screenshot...');
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
        throw new Error('No active tab');
    }

    const dataUrl = await chrome.tabs.captureVisibleTab(null, {
        format: 'png',
        quality: 85,
    });

    const base64 = dataUrl.split(',')[1];
    console.log('[Pilot BG] Screenshot captured, size:', base64.length);

    return {
        image: base64,
        tabId: tab.id,
        url: tab.url,
    };
}

// ---------------------------------------------------------------------------
// Action execution via chrome.debugger
// ---------------------------------------------------------------------------

async function attachDebugger(tabId) {
    if (attachedTabId === tabId) return;

    if (attachedTabId !== null) {
        try {
            await chrome.debugger.detach({ tabId: attachedTabId });
        } catch (e) { /* ignore */ }
    }

    await chrome.debugger.attach({ tabId }, '1.3');
    attachedTabId = tabId;
    console.log('[Pilot BG] Debugger attached to tab:', tabId);
}

async function executeAction(action, stepIndex) {
    console.log('[Pilot BG] Executing:', action.type, action);
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error('No active tab');

    await attachDebugger(tab.id);

    switch (action.type) {
        case 'click':
            await performClick(tab.id, action.x, action.y);
            break;
        case 'type':
            await performClick(tab.id, action.x, action.y);
            await sleep(300);
            await performType(tab.id, action.text);
            break;
        case 'scroll':
            await performScroll(tab.id, action.direction, action.amount || 300);
            break;
        case 'navigate':
            await chrome.tabs.update(tab.id, { url: action.url });
            await sleep(2000);
            break;
        case 'keypress':
            await performKeypress(tab.id, action.key);
            break;
    }

    console.log('[Pilot BG] Action done');

    // Notify the side panel
    chrome.runtime.sendMessage({
        type: 'action_executed',
        step_index: stepIndex,
        action: action,
    }).catch(() => { });
}

async function performClick(tabId, x, y) {
    const params = { type: 'mousePressed', x, y, button: 'left', clickCount: 1 };
    await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchMouseEvent', params);
    await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchMouseEvent', { ...params, type: 'mouseReleased' });
}

async function performType(tabId, text) {
    for (const char of text) {
        await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchKeyEvent', {
            type: 'keyDown', text: char, key: char, code: `Key${char.toUpperCase()}`,
        });
        await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchKeyEvent', {
            type: 'keyUp', key: char, code: `Key${char.toUpperCase()}`,
        });
        await sleep(50);
    }
}

async function performScroll(tabId, direction, amount) {
    const deltaY = direction === 'down' ? amount : -amount;
    await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchMouseEvent', {
        type: 'mouseWheel', x: 400, y: 400, deltaX: 0, deltaY,
    });
}

async function performKeypress(tabId, key) {
    const keyMap = {
        'Enter': { key: 'Enter', code: 'Enter', keyCode: 13 },
        'Tab': { key: 'Tab', code: 'Tab', keyCode: 9 },
        'Escape': { key: 'Escape', code: 'Escape', keyCode: 27 },
        'Backspace': { key: 'Backspace', code: 'Backspace', keyCode: 8 },
    };
    const mapped = keyMap[key] || { key, code: key, keyCode: 0 };
    await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchKeyEvent', { type: 'keyDown', ...mapped });
    await chrome.debugger.sendCommand({ tabId }, 'Input.dispatchKeyEvent', { type: 'keyUp', ...mapped });
}

// Open side panel on action click
chrome.action.onClicked.addListener((tab) => {
    chrome.sidePanel.open({ tabId: tab.id });
});

// Cleanup
chrome.debugger.onDetach.addListener((source) => {
    if (source.tabId === attachedTabId) attachedTabId = null;
});

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

console.log('[Pilot BG] Service worker loaded');
