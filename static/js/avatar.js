import { TalkingHead } from "talkinghead";

let head;
let documentContext = { extracted_content: "", explanation: "" };
let lastDocumentHash = ""; 

document.addEventListener('DOMContentLoaded', async function () {
    const avatarContainer = document.getElementById('avatar-container');
    const loadingIndicator = document.getElementById('avatar-loading');

    try {
        const contextResponse = await fetch('/avatar/context');
        if (contextResponse.ok) {
            documentContext = await contextResponse.json();
            console.log("Retrieved document context:", documentContext.extracted_content ? "Yes" : "No");
            
            if (documentContext.extracted_content) {
                lastDocumentHash = simpleHash(documentContext.extracted_content);
            }
        }
    } catch (error) {
        console.error("Error fetching document context:", error);
    }

    try {
        head = new TalkingHead(avatarContainer, {
            ttsEndpoint: "https://eu-texttospeech.googleapis.com/v1beta1/text:synthesize",
            ttsApikey: "<your_google_TTS_api_key>", 
            cameraView: "upper",
            cameraRotateEnable: true,
            avatarMood: "neutral",
            lipsyncLang: "en",
            ttsLang: "en-GB",
            ttsVoice: "en-GB-Standard-A",
            ttsRate: 1.0
        });

        loadingIndicator.textContent = "Loading avatar...";
        await head.showAvatar({
            url: '/static/models/avatar.glb',
            body: 'M',
            ttsLang: 'en-GB',
            ttsVoice: 'en-GB-Standard-A',
            lipsyncLang: 'en'
        }, (ev) => {
            if (ev.lengthComputable) {
                const val = Math.min(100, Math.round(ev.loaded / ev.total * 100));
                loadingIndicator.textContent = `Loading ${val}%`;
            }
        });

        loadingIndicator.style.display = 'none';
        
        if (documentContext.extracted_content) {
            head.speakText("Hello! I'm your AI assistant. I've read the document you uploaded. Feel free to ask me any questions about it.");
        } else {
            head.speakText("Hello! I'm your AI assistant. Ask me anything.");
        }

    } catch (error) {
        console.error("Error loading avatar:", error);
        loadingIndicator.textContent = "Error loading avatar: " + error.message;
    }

    setupChatInteraction();
    setupBackButton();
    setupDocumentRefresh();
});

function simpleHash(str) {
    if (!str) return "empty";
    
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; 
    }
    return String(hash);
}

function setupDocumentRefresh() {
    setInterval(async () => {
        try {
            const contextResponse = await fetch('/avatar/context');
            if (contextResponse.ok) {
                const newContext = await contextResponse.json();
                
                if (!newContext.extracted_content) {
                    documentContext = newContext;
                    return;
                }
                
                const newHash = simpleHash(newContext.extracted_content);
                if (newHash !== lastDocumentHash) {
                    console.log("Document context has changed, updating...");
                    documentContext = newContext;
                    lastDocumentHash = newHash;
                    
                    if (newContext.extracted_content && newContext.extracted_content.trim() !== "") {
                        head.speakText("I've just received a new document. Feel free to ask me questions about it.");
                        addMessageToChat('assistant', "I've just received a new document. Feel free to ask me questions about it.");
                    }
                }
            }
        } catch (error) {
            console.error("Error refreshing document context:", error);
        }
    }, 5000);
}

function setupBackButton() {
    const backButton = document.querySelector('.back-button');
    
    if (backButton) {
        backButton.addEventListener('click', function(event) {
            event.preventDefault();
            
            window.history.back();
        });
    }
}


function setupChatInteraction() {
    const textInput = document.getElementById('text-input');
    const sendTextButton = document.getElementById('send-text');
    const startRecordingButton = document.getElementById('start-recording');
    const stopRecordingButton = document.getElementById('stop-recording');
    const chatHistoryContainer = document.getElementById('chat-history');

    let mediaRecorder;
    let audioChunks = [];
    let isProcessing = false; 

    const thinkingPhrases = [
        "⏳ Thinking...",
        "⏳ Let me think about that...",
        "⏳ Processing your question...",
        "⏳ Looking into that...",
        "⏳ One moment..."
    ];

    const greetingPhrases = [
        "Hello! I'm your AI assistant. I've read the document you uploaded. Feel free to ask me any questions about it.",
        "Hi there! I've analyzed your document and I'm ready to chat about it. What would you like to know?",
        "Hey! I've gone through your document and I'm here to help. What can I explain for you?",
        "Welcome! I've processed your document and I'm ready to discuss it. What questions do you have?"
    ];

    sendTextButton.addEventListener('click', async () => {
        const userInput = textInput.value.trim();
        if (userInput && !isProcessing) {
            await processUserInput(userInput, 'text');
            textInput.value = '';
        }
    });

    textInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter' && !isProcessing) {
            const userInput = textInput.value.trim();
            if (userInput) {
                await processUserInput(userInput, 'text');
                textInput.value = '';
            }
        }
    });

    startRecordingButton.addEventListener('click', async () => {
        if (isProcessing) return;
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks);
                await processUserInput(audioBlob, 'audio');
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            startRecordingButton.disabled = true;
            stopRecordingButton.disabled = false;
        } catch (error) {
            console.error("Microphone access error:", error);
            alert("Cannot access microphone. Please check browser permissions.");
        }
    });

    stopRecordingButton.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            startRecordingButton.disabled = false;
            stopRecordingButton.disabled = true;
        }
    });

    async function processUserInput(input, type) {
        if (isProcessing) return;
        isProcessing = true;
        
        if (type === 'text') {
            addMessageToChat('user', input);
        } else {
            addMessageToChat('user', '🎤 [Audio message]');
        }

        try {
            const formData = new FormData();
            if (type === 'text') {
                formData.append('input', input);
                formData.append('type', 'text');
            } else {
                formData.append('audio', input);
                formData.append('type', 'audio');
            }

            const randomThinking = thinkingPhrases[Math.floor(Math.random() * thinkingPhrases.length)];
            const loadingMessage = addMessageToChat('assistant', randomThinking);

            const response = await fetch('/avatar/chat', {
                method: 'POST',
                body: formData
            });

            loadingMessage.remove();

            if (response.ok) {
                const data = await response.json();

                if (data.text && data.text.trim() !== "") {
                    addMessageToChat('assistant', data.text);
                    try {
                        setTimeout(() => {
                            head.speakText(data.text);
                        }, 300);
                    } catch (speakError) {
                        console.error("TTS failed:", speakError);
                    }
                } else {
                    addMessageToChat('assistant', "Sorry, I didn't get a proper response.");
                }

            } else {
                addMessageToChat('assistant', "Sorry, I couldn't process your request.");
            }
        } catch (error) {
            console.error("Chat processing error:", error);
            addMessageToChat('assistant', "Sorry, something went wrong.");
        } finally {
            isProcessing = false;
        }
    }

    window.addMessageToChat = function(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${sender}-message`;

        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        contentElement.textContent = text;

        messageElement.appendChild(contentElement);
        chatHistoryContainer.appendChild(messageElement);
        chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;

        return messageElement;
    }
    
    document.addEventListener('DOMContentLoaded', async function() {
        
        if (documentContext.extracted_content) {
            const randomGreeting = greetingPhrases[Math.floor(Math.random() * greetingPhrases.length)];
            head.speakText(randomGreeting);
        } else {
            head.speakText("Hello! I'm your AI assistant. Ask me anything.");
        }
    });
}
