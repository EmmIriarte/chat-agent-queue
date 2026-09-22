"""Dashboard routes for queue visualization"""
import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the queue dashboard UI"""
    try:
        with open("static/dashboard.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Agent Queue Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 16px;
        }
        
        /* AI Toggle (per conversation) */
        .conversation-ai-toggle {
            display: flex;
            align-items: center;
            gap: 12px;
            background: #f8f9fa;
            padding: 10px 16px;
            border-radius: 25px;
            border: 2px solid #e0e0e0;
            margin-bottom: 15px;
        }
        
        .toggle-switch {
            position: relative;
            width: 56px;
            height: 30px;
            display: inline-block;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: 0.4s;
            border-radius: 30px;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 22px;
            width: 22px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: 0.4s;
            border-radius: 50%;
        }
        
        input:checked + .toggle-slider {
            background-color: #4CAF50;
        }
        
        input:checked + .toggle-slider:before {
            transform: translateX(26px);
        }
        
        .toggle-label {
            font-weight: 600;
            color: #333;
            font-size: 15px;
        }
        
        .ai-status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ccc;
            animation: pulse 2s infinite;
        }
        
        .ai-status-indicator.active {
            background: #4CAF50;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 10px;
            background: white;
            padding: 10px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .tab {
            padding: 12px 24px;
            background: #f5f5f5;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
        }
        
        .tab:hover {
            background: #e0e0e0;
        }
        
        .tab.active {
            background: #667eea;
            color: white;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .stat-label {
            color: #666;
            font-size: 14px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .stat-value {
            font-size: 36px;
            font-weight: 700;
            color: #333;
        }
        
        .stat-value.scheduled { color: #f59e0b; }
        .stat-value.sent { color: #10b981; }
        .stat-value.error { color: #ef4444; }
        .stat-value.total { color: #667eea; }
        
        /* Conversations */
        .conversation-layout {
            display: grid;
            grid-template-columns: 400px 1fr;
            gap: 20px;
            height: 70vh;
        }
        
        .conversation-list {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-y: auto;
        }
        
        .conversation-item {
            padding: 16px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .conversation-item:hover {
            background: #f9fafb;
        }
        
        .conversation-item.active {
            background: #eef2ff;
            border-left: 4px solid #667eea;
        }
        
        .conversation-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .conversation-id {
            font-size: 12px;
            color: #666;
            font-family: monospace;
        }
        
        .conversation-stage {
            display: inline-block;
            padding: 4px 8px;
            background: #667eea;
            color: white;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        
        .conversation-preview {
            font-size: 14px;
            color: #666;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .conversation-meta {
            font-size: 12px;
            color: #999;
            margin-top: 8px;
        }
        
        .conversation-detail {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        .conversation-detail.empty {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 18px;
        }
        
        .message-history {
            flex: 1;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 16px;
            padding: 12px;
            border-radius: 8px;
        }
        
        .message.outbound {
            background: #eef2ff;
            border-left: 4px solid #667eea;
        }
        
        .message.inbound {
            background: #f0fdf4;
            border-left: 4px solid #10b981;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .message-direction {
            font-weight: 600;
            color: #333;
        }
        
        .message-direction.outbound::before {
            content: "📤 ";
        }
        
        .message-direction.inbound::before {
            content: "📨 ";
        }
        
        .message-time {
            font-size: 12px;
            color: #999;
        }
        
        .message-content {
            color: #333;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        
        .message-attachment {
            margin-top: 8px;
            padding: 8px;
            background: white;
            border-radius: 4px;
            font-size: 12px;
            color: #667eea;
        }
        
        .message-attachment::before {
            content: "📎 ";
        }
        
        /* Queue Table */
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .card h2 {
            color: #333;
            font-size: 24px;
            margin-bottom: 20px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background: #f9fafb;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #666;
            font-size: 14px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            color: #333;
            font-size: 14px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-scheduled {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-sent {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-error {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .cancel-btn {
            padding: 6px 12px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s;
        }
        
        .cancel-btn:hover {
            background: #dc2626;
        }
        
        .cancel-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        /* Test Form */
        .test-form {
            display: grid;
            gap: 16px;
            margin-top: 24px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
        }
        
        .form-group.full-width {
            grid-column: 1 / -1;
        }
        
        label {
            margin-bottom: 8px;
            color: #666;
            font-weight: 500;
            font-size: 14px;
        }
        
        input, select, textarea {
            padding: 10px 12px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
        }
        
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        
        .checkbox-group {
            display: flex;
            gap: 16px;
            margin-top: 8px;
        }
        
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }
        
        input[type="checkbox"] {
            width: auto;
        }
        
        .submit-btn {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .submit-btn:hover {
            background: #5a67d8;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Chat Agent Queue Dashboard</h1>
            <p>Real-time conversation monitoring and queue management</p>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('conversations')">💬 Conversations</button>
            <button class="tab" onclick="switchTab('queue')">📊 Queue Status</button>
            <button class="tab" onclick="switchTab('test')">🧪 Quick Test</button>
        </div>
        
        <!-- Conversations Tab -->
        <div id="conversations-tab" class="tab-content active">
            <div class="conversation-layout">
                <div class="conversation-list" id="conversation-list">
                    <div class="loading">Loading conversations...</div>
                </div>
                <div class="conversation-detail empty" id="conversation-detail">
                    Select a conversation to view history
                </div>
            </div>
        </div>
        
        <!-- Queue Tab -->
        <div id="queue-tab" class="tab-content">
            <!-- Stats -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Messages</div>
                    <div class="stat-value total" id="stat-total">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Scheduled</div>
                    <div class="stat-value scheduled" id="stat-scheduled">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Sent</div>
                    <div class="stat-value sent" id="stat-sent">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Errors</div>
                    <div class="stat-value error" id="stat-error">0</div>
                </div>
            </div>
            
            <!-- Messages Table -->
            <div class="card">
                <h2>Queue Messages</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Type</th>
                            <th>Scheduled At</th>
                            <th>Message Preview</th>
                            <th>Retry</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="messages-table">
                        <tr>
                            <td colspan="6" class="loading">Loading messages...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Test Tab -->
        <div id="test-tab" class="tab-content">
            <div class="card">
                <h2>Quick Test Message</h2>
                <form class="test-form" id="test-form">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Account</label>
                            <select id="account-select" required>
                                <option value="">Loading accounts...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Recipient LinkedIn ID</label>
                            <input type="text" id="recipient-id" required placeholder="e.g., ACoAAAcDMMQB...">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label>Job ID</label>
                            <input type="text" id="job-id" required placeholder="e.g., job_123">
                        </div>
                        <div class="form-group">
                            <label>Unipile Account ID (auto-filled)</label>
                            <input type="text" id="unipile-account-id" readonly>
                        </div>
                    </div>
                    
                    <div class="form-group full-width">
                        <label>Message</label>
                        <textarea id="message" required placeholder="Enter your message here..."></textarea>
                    </div>
                    
                    <div class="form-group full-width">
                        <label>Options</label>
                        <div class="checkbox-group">
                            <label class="checkbox-label">
                                <input type="checkbox" id="is-invite">
                                <span>Is Invite</span>
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" id="is-initial">
                                <span>Initial Reach-out</span>
                            </label>
                        </div>
                    </div>
                    
                    <button type="submit" class="submit-btn">📤 Send to Queue</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        let selectedChatId = null;
        
        // Notification helper
        function showNotification(message, color) {
            const notification = document.createElement('div');
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 25px;
                background: ${color};
                color: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                z-index: 10000;
                font-weight: 600;
                animation: slideInRight 0.3s ease;
            `;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
        
        // Tab switching
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(tabName + '-tab').classList.add('active');
            
            // Refresh data when switching to conversations or queue
            if (tabName === 'conversations') {
                loadConversations();
            } else if (tabName === 'queue') {
                loadQueueData();
            }
        }
        
        // Load conversations
        async function loadConversations() {
            try {
                const response = await fetch('/api/v1/internal/conversations');
                const data = await response.json();
                
                const listEl = document.getElementById('conversation-list');
                
                if (!data.conversations || data.conversations.length === 0) {
                    listEl.innerHTML = '<div class="empty-state">No conversations yet</div>';
                    return;
                }
                
                listEl.innerHTML = data.conversations.map(conv => `
                    <div class="conversation-item" onclick="loadConversationHistory('${conv.chat_id}')">
                        <div class="conversation-header">
                            <span class="conversation-id">${conv.chat_id.substring(0, 8)}...</span>
                            <span class="conversation-stage">${conv.stage}</span>
                        </div>
                        <div class="conversation-preview">${conv.last_message_preview || 'No messages yet'}</div>
                        <div class="conversation-meta">
                            ${conv.message_count} messages • Job: ${conv.job_id}
                        </div>
                    </div>
                `).join('');
                
            } catch (error) {
                console.error('Error loading conversations:', error);
            }
        }
        
        // Load conversation history
        async function loadConversationHistory(chatId) {
            selectedChatId = chatId;
            
            // Update active state
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('active');
            });
            event.target.closest('.conversation-item').classList.add('active');
            
            try {
                const response = await fetch(`/api/v1/internal/conversations/${chatId}/history`);
                const data = await response.json();
                
                const detailEl = document.getElementById('conversation-detail');
                detailEl.classList.remove('empty');
                
                if (!data.history || data.history.length === 0) {
                    detailEl.innerHTML = '<div class="empty-state">No messages in this conversation yet</div>';
                    return;
                }
                
                // Get AI status from conversations endpoint
                const jobId = data.conversation.job_id || 'unknown';
                let aiEnabled = true;
                
                try {
                    // Try to get AI status from loaded conversations
                    const convResponse = await fetch(`/api/v1/internal/jobs/${jobId}`);
                    const convData = await convResponse.json();
                    const conv = convData.conversations?.find(c => c.chat_id === chatId);
                    if (conv) {
                        aiEnabled = conv.ai_enabled !== undefined ? conv.ai_enabled : true;
                    }
                } catch (e) {
                    console.warn('Could not fetch AI status:', e);
                }
                
                detailEl.innerHTML = `
                    <div style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #eee;">
                        <h3 style="color: #333; margin-bottom: 8px;">Conversation Details</h3>
                        <p style="color: #666; font-size: 14px;">
                            Stage: <strong>${data.conversation.stage}</strong> • 
                            Messages: <strong>${data.conversation.message_count}</strong>
                        </p>
                        
                        <div class="conversation-ai-toggle" style="margin-top: 12px;">
                            <div class="ai-status-indicator ${aiEnabled ? 'active' : ''}" id="conv-ai-indicator-${chatId}"></div>
                            <span class="toggle-label" style="font-size: 14px;">AI Auto-Reply for this conversation</span>
                            <label class="toggle-switch">
                                <input type="checkbox" id="conv-ai-toggle-${chatId}" ${aiEnabled ? 'checked' : ''} 
                                    onchange="toggleConversationAI('${chatId}', this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>
                    <div class="message-history">
                        ${data.history.map(msg => {
                            const err = msg.error;
                            const errHtml = err && (err.title || err.detail)
                                ? `<div class="error-detail" style="margin-top:8px;padding:8px;background:#fef2f2;border-radius:6px;color:#991b1b;font-size:13px">
                                    ${err.title ? `<strong>${err.title}</strong><br>` : ''}
                                    ${err.detail || msg.error_message || ''}
                                    ${err.type ? `<br><code style="font-size:11px">${err.type}</code>` : ''}
                                   </div>`
                                : (msg.error_message ? `<div class="error-detail" style="margin-top:8px;color:#991b1b">${msg.error_message}</div>` : '');
                            return `
                            <div class="message ${msg.direction}">
                                <div class="message-header">
                                    <span class="message-direction ${msg.direction}">
                                        ${msg.direction === 'outbound' ? 'Sent' : 'Received'}
                                    </span>
                                    <span class="message-time">${new Date(msg.timestamp).toLocaleString()}</span>
                                    ${msg.status ? `<span class="status-badge status-${msg.status}">${msg.status}</span>` : ''}
                                </div>
                                <div class="message-content">${msg.message}</div>
                                ${msg.has_attachment ? `<div class="message-attachment">${msg.attachment_info}</div>` : ''}
                                ${errHtml}
                            </div>`;
                        }).join('')}
                    </div>
                `;
                
                // Scroll to bottom
                const historyEl = detailEl.querySelector('.message-history');
                historyEl.scrollTop = historyEl.scrollHeight;
                
            } catch (error) {
                console.error('Error loading conversation history:', error);
            }
        }
        
        // Toggle AI for a specific conversation
        async function toggleConversationAI(chatId, enabled) {
            try {
                const response = await fetch(
                    `/api/v1/internal/conversations/${chatId}/ai/toggle?enabled=${enabled}`,
                    { method: 'POST' }
                );
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    const indicator = document.getElementById(`conv-ai-indicator-${chatId}`);
                    if (indicator) {
                        if (enabled) {
                            indicator.classList.add('active');
                            showNotification(`🤖 AI enabled for this conversation`, '#4CAF50');
                        } else {
                            indicator.classList.remove('active');
                            showNotification(`⏸️ AI disabled for this conversation`, '#FF9800');
                        }
                    }
                }
            } catch (error) {
                console.error('Error toggling conversation AI:', error);
                document.getElementById(`conv-ai-toggle-${chatId}`).checked = !enabled;
                showNotification('❌ Failed to toggle AI', '#F44336');
            }
        }
        
        // Load queue data
        async function loadQueueData() {
            try {
                const [statusRes, messagesRes] = await Promise.all([
                    fetch('/api/v1/internal/status/queues'),
                    fetch('/api/v1/internal/messages/all')
                ]);
                
                const status = await statusRes.json();
                const messages = await messagesRes.json();
                
                // Update stats
                document.getElementById('stat-total').textContent = status.total_messages || 0;
                document.getElementById('stat-scheduled').textContent = status.scheduled || 0;
                document.getElementById('stat-sent').textContent = status.sent || 0;
                document.getElementById('stat-error').textContent = status.error || 0;
                
                // Update table
                const tbody = document.getElementById('messages-table');
                if (!messages.messages || messages.messages.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No messages in queue</td></tr>';
                    return;
                }
                
                tbody.innerHTML = messages.messages.map(msg => {
                    const err = msg.error;
                    const errHint = err && (err.title || err.detail)
                        ? (err.title || err.detail)
                        : (msg.error_message ? String(msg.error_message).slice(0, 80) : '');
                    return `
                    <tr>
                        <td><span class="status-badge status-${msg.status}">${msg.status}</span></td>
                        <td>${msg.message_type === 'invite' ? '🤝 INVITE' : '💬 MESSAGE'}</td>
                        <td>${msg.scheduled_at ? new Date(msg.scheduled_at).toLocaleString() : '-'}</td>
                        <td>${msg.message.substring(0, 50)}...</td>
                        <td>${msg.retry_count}/3</td>
                        <td title="${errHint.replace(/"/g, '&quot;')}">
                            ${errHint ? `<span style="color:#b91c1c;font-size:12px">${errHint}</span><br>` : ''}
                            ${msg.status === 'scheduled' ? `
                                <button class="cancel-btn" onclick="cancelMessage('${msg.message_id}')">Cancel</button>
                            ` : '-'}
                        </td>
                    </tr>`;
                }).join('');
                
            } catch (error) {
                console.error('Error loading queue data:', error);
            }
        }
        
        // Cancel message
        async function cancelMessage(messageId) {
            if (!confirm('Cancel this message?')) return;
            
            try {
                const response = await fetch(`/api/v1/internal/messages/${messageId}/cancel`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    loadQueueData();
                } else {
                    alert('Failed to cancel message');
                }
            } catch (error) {
                console.error('Error cancelling message:', error);
                alert('Error cancelling message');
            }
        }
        
        // Load accounts
        async function loadAccounts() {
            try {
                const response = await fetch('/api/v1/supabase/accounts/list');
                const data = await response.json();
                
                const select = document.getElementById('account-select');
                
                if (data.accounts && data.accounts.length > 0) {
                    select.innerHTML = '<option value="">Select an account...</option>' +
                        data.accounts.map(acc => `
                            <option value="${acc.account_id}" data-provider="${acc.provider_id}">
                                ${acc.name || acc.account_id}
                            </option>
                        `).join('');
                } else {
                    select.innerHTML = '<option value="">No accounts found</option>';
                }
            } catch (error) {
                console.error('Error loading accounts:', error);
            }
        }
        
        // Account select change
        document.addEventListener('DOMContentLoaded', () => {
            const accountSelect = document.getElementById('account-select');
            const unipileAccountInput = document.getElementById('unipile-account-id');
            
            accountSelect.addEventListener('change', (e) => {
                unipileAccountInput.value = e.target.value;
            });
        });
        
        // Test form submission
        document.getElementById('test-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                unipile_account_id: document.getElementById('unipile-account-id').value,
                recipient_linkedin_id: document.getElementById('recipient-id').value,
                job_id: document.getElementById('job-id').value,
                message: document.getElementById('message').value,
                is_invite: document.getElementById('is-invite').checked,
                is_initial_reachout: document.getElementById('is-initial').checked
            };
            
            try {
                const response = await fetch('/api/v1/internal/messages/enqueue', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('✅ Message queued successfully!');
                    document.getElementById('test-form').reset();
                } else {
                    alert('❌ Error: ' + (result.detail || 'Failed to queue message'));
                }
            } catch (error) {
                console.error('Error submitting form:', error);
                alert('❌ Network error');
            }
        });
        
        // Auto-refresh conversations every 5 seconds
        setInterval(() => {
            const activeTab = document.querySelector('.tab-content.active');
            if (activeTab.id === 'conversations-tab') {
                loadConversations();
                if (selectedChatId) {
                    loadConversationHistory(selectedChatId);
                }
            } else if (activeTab.id === 'queue-tab') {
                loadQueueData();
            }
        }, 5000);
        
        // Initial load
        loadConversations();
        loadAccounts();
    </script>
</body>
</html>
        """
