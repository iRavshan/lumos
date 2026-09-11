(function () {
    'use strict';

    // Locate current script and business key
    var currentScript = document.currentScript || (function () {
        var scripts = document.getElementsByTagName('script');
        for (var i = scripts.length - 1; i >= 0; i--) {
            if (scripts[i].src && scripts[i].src.indexOf('lumos-widget.js') !== -1) {
                return scripts[i];
            }
        }
        return scripts[scripts.length - 1];
    })();

    var businessKey = currentScript.getAttribute('data-business-key') || window.LUMOS_BUSINESS_KEY;
    if (!businessKey) {
        console.error('Lumos Chatbot Widget: data-business-key atributi ko\'rsatilmadi!');
        return;
    }

    // Determine Base URL from script src
    var baseUrl = '';
    if (currentScript && currentScript.src) {
        var a = document.createElement('a');
        a.href = currentScript.src;
        baseUrl = a.protocol + '//' + a.host;
    } else {
        baseUrl = window.location.protocol + '//' + window.location.host;
    }

    // Generate or fetch session ID
    var storageKey = 'lumos_session_' + businessKey;
    var sessionId = localStorage.getItem(storageKey);
    if (!sessionId) {
        sessionId = 'sess_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        localStorage.setItem(storageKey, sessionId);
    }

    // Load configuration from API
    fetch(baseUrl + '/api/v1/' + businessKey + '/config/')
        .then(function (res) { return res.json(); })
        .then(function (config) {
            if (!config || !config.is_active) {
                console.log('Lumos Chatbot Widget: Chatbot nofaol holatda.');
                return;
            }
            initWidget(config);
        })
        .catch(function (err) {
            console.error('Lumos Chatbot Widget yuklanishida xatolik:', err);
        });

    function initWidget(config) {
        var themeColor = config.theme_color || '#4f46e5';
        var botName = config.bot_name || 'AI Yordamchi';
        var businessName = config.business_name || 'Biznes';
        var welcomeMsg = config.welcome_message || 'Assalomu alaykum! Sizga qanday yordam bera olaman?';
        var logoUrl = config.business_logo_url ? (baseUrl + config.business_logo_url) : null;

        // Inject Styles
        var style = document.createElement('style');
        style.innerHTML = `
            .lumos-widget-container * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
            .lumos-float-btn {
                position: fixed;
                bottom: 24px;
                right: 24px;
                width: 60px;
                height: 60px;
                border-radius: 30px;
                background-color: ${themeColor};
                color: #ffffff;
                border: none;
                cursor: pointer;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 999999;
                transition: transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.25s ease;
            }
            .lumos-float-btn:hover {
                transform: scale(1.08);
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
            }
            .lumos-float-btn svg { width: 28px; height: 28px; fill: currentColor; }
            
            .lumos-chat-window {
                position: fixed;
                bottom: 96px;
                right: 24px;
                width: 380px;
                max-width: calc(100vw - 32px);
                height: 580px;
                max-height: calc(100vh - 120px);
                background: #ffffff;
                border-radius: 20px;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16);
                display: flex;
                flex-direction: column;
                z-index: 999999;
                overflow: hidden;
                border: 1px solid rgba(0, 0, 0, 0.08);
                opacity: 0;
                transform: translateY(20px) scale(0.95);
                pointer-events: none;
                transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }
            .lumos-chat-window.open {
                opacity: 1;
                transform: translateY(0) scale(1);
                pointer-events: auto;
            }

            .lumos-chat-header {
                background: ${themeColor};
                color: #ffffff;
                padding: 16px 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .lumos-header-info { display: flex; align-items: center; gap: 12px; }
            .lumos-avatar {
                width: 38px;
                height: 38px;
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 16px;
            }
            .lumos-title-wrap h4 { margin: 0; font-size: 15px; font-weight: 700; line-height: 1.2; }
            .lumos-title-wrap p { margin: 2px 0 0; font-size: 12px; opacity: 0.85; display: flex; align-items: center; gap: 5px; }
            .lumos-status-dot { width: 7px; height: 7px; background: #10b981; border-radius: 50%; }

            .lumos-close-btn {
                background: rgba(255, 255, 255, 0.15);
                border: none;
                color: #ffffff;
                width: 32px;
                height: 32px;
                border-radius: 10px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                transition: background 0.15s;
            }
            .lumos-close-btn:hover { background: rgba(255, 255, 255, 0.3); }

            .lumos-chat-body {
                flex: 1;
                padding: 16px;
                overflow-y: auto;
                background: #f8fafc;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .lumos-message {
                max-width: 82%;
                padding: 11px 15px;
                border-radius: 16px;
                font-size: 13.5px;
                line-height: 1.5;
                word-wrap: break-word;
                white-space: pre-wrap;
            }
            .lumos-msg-bot {
                align-self: flex-start;
                background: #ffffff;
                color: #1e293b;
                border-bottom-left-radius: 4px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
                border: 1px solid #f1f5f9;
            }
            .lumos-msg-user {
                align-self: flex-end;
                background: ${themeColor};
                color: #ffffff;
                border-bottom-right-radius: 4px;
            }

            .lumos-typing-indicator {
                align-self: flex-start;
                background: #ffffff;
                padding: 10px 14px;
                border-radius: 16px;
                border-bottom-left-radius: 4px;
                display: none;
                align-items: center;
                gap: 4px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
                border: 1px solid #f1f5f9;
            }
            .lumos-typing-indicator.active { display: flex; }
            .lumos-typing-dot {
                width: 6px;
                height: 6px;
                background: #94a3b8;
                border-radius: 50%;
                animation: lumos-bounce 1.4s infinite ease-in-out both;
            }
            .lumos-typing-dot:nth-child(1) { animation-delay: -0.32s; }
            .lumos-typing-dot:nth-child(2) { animation-delay: -0.16s; }
            @keyframes lumos-bounce {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }

            .lumos-chat-footer {
                padding: 12px 14px;
                background: #ffffff;
                border-top: 1px solid #f1f5f9;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .lumos-input {
                flex: 1;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13.5px;
                outline: none;
                transition: border-color 0.15s;
                background: #f8fafc;
            }
            .lumos-input:focus {
                border-color: ${themeColor};
                background: #ffffff;
            }
            .lumos-send-btn {
                background: ${themeColor};
                color: #ffffff;
                border: none;
                width: 38px;
                height: 38px;
                border-radius: 12px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: opacity 0.15s;
            }
            .lumos-send-btn:hover { opacity: 0.9; }
            .lumos-send-btn svg { width: 18px; height: 18px; fill: currentColor; }

            .lumos-branding {
                text-align: center;
                font-size: 10.5px;
                color: #94a3b8;
                padding: 4px 0 6px;
                background: #ffffff;
            }
            .lumos-branding a { color: #64748b; text-decoration: none; font-weight: 600; }
        `;
        document.head.appendChild(style);

        // Build HTML
        var container = document.createElement('div');
        container.className = 'lumos-widget-container';
        container.innerHTML = `
            <button class="lumos-float-btn" id="lumosFloatBtn" aria-label="Chatbotni ochish">
                <svg viewBox="0 0 24 24">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                </svg>
            </button>

            <div class="lumos-chat-window" id="lumosChatWindow">
                <div class="lumos-chat-header">
                    <div class="lumos-header-info">
                        <div class="lumos-avatar">${logoUrl ? '<img src="' + logoUrl + '" style="width:100%;height:100%;object-fit:contain;padding:3px;" onerror="this.style.display=\'none\'; this.parentElement.textContent=\'' + businessName.charAt(0).toUpperCase() + '\'">' : businessName.charAt(0).toUpperCase()}</div>
                        <div class="lumos-title-wrap">
                            <h4>${botName}</h4>
                            <p><span class="lumos-status-dot"></span> ${businessName}</p>
                        </div>
                    </div>
                    <button class="lumos-close-btn" id="lumosCloseBtn" aria-label="Yopish">&times;</button>
                </div>

                <div class="lumos-chat-body" id="lumosChatBody">
                    <div class="lumos-message lumos-msg-bot">${welcomeMsg}</div>

                    <div class="lumos-typing-indicator" id="lumosTyping">
                        <div class="lumos-typing-dot"></div>
                        <div class="lumos-typing-dot"></div>
                        <div class="lumos-typing-dot"></div>
                    </div>
                </div>

                <form class="lumos-chat-footer" id="lumosChatForm">
                    <input type="text" class="lumos-input" id="lumosInput" placeholder="Savolingizni yozing..." autocomplete="off">
                    <button type="submit" class="lumos-send-btn" id="lumosSendBtn" aria-label="Yuborish">
                        <svg viewBox="0 0 24 24">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </form>
                <div class="lumos-branding">
                    Powered by <a href="${baseUrl}" target="_blank">Lumos AI</a>
                </div>
            </div>
        `;
        document.body.appendChild(container);

        var floatBtn = document.getElementById('lumosFloatBtn');
        var chatWindow = document.getElementById('lumosChatWindow');
        var closeBtn = document.getElementById('lumosCloseBtn');
        var chatBody = document.getElementById('lumosChatBody');
        var chatForm = document.getElementById('lumosChatForm');
        var chatInput = document.getElementById('lumosInput');
        var typingIndicator = document.getElementById('lumosTyping');

        var isOpen = false;

        function toggleChat() {
            isOpen = !isOpen;
            if (isOpen) {
                chatWindow.classList.add('open');
                chatInput.focus();
            } else {
                chatWindow.classList.remove('open');
            }
        }

        floatBtn.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', toggleChat);

        function scrollToBottom() {
            chatBody.scrollTop = chatBody.scrollHeight;
        }

        function appendMessage(text, role) {
            var msgDiv = document.createElement('div');
            msgDiv.className = 'lumos-message ' + (role === 'user' ? 'lumos-msg-user' : 'lumos-msg-bot');
            msgDiv.textContent = text;
            chatBody.insertBefore(msgDiv, typingIndicator);
            scrollToBottom();
        }

        function sendMessage(text) {
            if (!text || !text.trim()) return;
            text = text.trim();

            appendMessage(text, 'user');
            chatInput.value = '';

            typingIndicator.classList.add('active');
            scrollToBottom();

            fetch(baseUrl + '/api/v1/' + businessKey + '/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId
                })
            })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                var delayMs = (data.delay_seconds || 0) * 1000;
                setTimeout(function () {
                    typingIndicator.classList.remove('active');
                    if (data.parts && data.parts.length > 1) {
                        data.parts.forEach(function (part, index) {
                            setTimeout(function () {
                                appendMessage(part, 'assistant');
                            }, index * 800);
                        });
                    } else if (data.reply) {
                        appendMessage(data.reply, 'assistant');
                    } else if (data.error) {
                        appendMessage('Xatolik: ' + data.error, 'assistant');
                    }
                }, delayMs);
            })
            .catch(function (err) {
                typingIndicator.classList.remove('active');
                appendMessage('Server bilan bog\'lanishda xatolik yuz berdi.', 'assistant');
            });
        }

        chatForm.addEventListener('submit', function (e) {
            e.preventDefault();
            sendMessage(chatInput.value);
        });
    }
})();
