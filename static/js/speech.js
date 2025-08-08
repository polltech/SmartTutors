// Text-to-Speech functionality for AI Smart Tutor
class SpeechManager {
    constructor() {
        this.synth = window.speechSynthesis;
        this.voices = [];
        this.currentUtterance = null;
        this.isInitialized = false;
        this.settings = {
            rate: 0.9,
            pitch: 1,
            volume: 0.8,
            voice: null
        };
        
        this.init();
    }

    init() {
        if (!this.synth) {
            console.warn('Speech synthesis not supported in this browser');
            return;
        }

        // Load voices when available
        this.loadVoices();
        
        // Some browsers require user interaction first
        document.addEventListener('click', () => {
            if (!this.isInitialized) {
                this.loadVoices();
                this.isInitialized = true;
            }
        }, { once: true });

        // Listen for voices changed event
        this.synth.onvoiceschanged = () => {
            this.loadVoices();
        };
    }

    loadVoices() {
        this.voices = this.synth.getVoices();
        
        // Prefer English voices
        const englishVoices = this.voices.filter(voice => 
            voice.lang.startsWith('en-') || voice.lang === 'en'
        );
        
        // Try to find a good default voice
        if (englishVoices.length > 0) {
            // Prefer female voices for educational content
            const femaleVoice = englishVoices.find(voice => 
                voice.name.toLowerCase().includes('female') ||
                voice.name.toLowerCase().includes('woman') ||
                voice.name.toLowerCase().includes('samantha') ||
                voice.name.toLowerCase().includes('karen') ||
                voice.name.toLowerCase().includes('victoria')
            );
            
            this.settings.voice = femaleVoice || englishVoices[0];
        } else if (this.voices.length > 0) {
            this.settings.voice = this.voices[0];
        }

        console.log(`Loaded ${this.voices.length} voices, selected:`, this.settings.voice?.name);
    }

    speak(text, options = {}) {
        if (!this.synth) {
            console.warn('Speech synthesis not available');
            return;
        }

        // Stop any current speech
        this.stop();

        // Clean and prepare text
        const cleanText = this.prepareText(text);
        if (!cleanText.trim()) {
            console.warn('No text to speak');
            return;
        }

        // Create utterance
        const utterance = new SpeechSynthesisUtterance(cleanText);
        
        // Apply settings
        utterance.rate = options.rate || this.settings.rate;
        utterance.pitch = options.pitch || this.settings.pitch;
        utterance.volume = options.volume || this.settings.volume;
        utterance.voice = options.voice || this.settings.voice;

        // Event handlers
        utterance.onstart = () => {
            console.log('Speech started');
            this.onSpeechStart();
        };

        utterance.onend = () => {
            console.log('Speech ended');
            this.onSpeechEnd();
            this.currentUtterance = null;
        };

        utterance.onerror = (event) => {
            console.error('Speech error:', event.error);
            this.onSpeechError(event.error);
            this.currentUtterance = null;
        };

        utterance.onpause = () => {
            console.log('Speech paused');
            this.onSpeechPause();
        };

        utterance.onresume = () => {
            console.log('Speech resumed');
            this.onSpeechResume();
        };

        // Store current utterance
        this.currentUtterance = utterance;

        // Start speaking
        try {
            this.synth.speak(utterance);
        } catch (error) {
            console.error('Failed to start speech:', error);
            this.currentUtterance = null;
        }
    }

    stop() {
        if (this.synth) {
            this.synth.cancel();
        }
        this.currentUtterance = null;
        this.onSpeechEnd();
    }

    pause() {
        if (this.synth && this.synth.speaking && !this.synth.paused) {
            this.synth.pause();
        }
    }

    resume() {
        if (this.synth && this.synth.paused) {
            this.synth.resume();
        }
    }

    isSpeaking() {
        return this.synth && this.synth.speaking;
    }

    isPaused() {
        return this.synth && this.synth.paused;
    }

    prepareText(text) {
        if (!text) return '';
        
        // Remove HTML tags
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = text;
        let cleanText = tempDiv.textContent || tempDiv.innerText || '';
        
        // Clean up common formatting issues
        cleanText = cleanText
            .replace(/\s+/g, ' ') // Replace multiple spaces with single space
            .replace(/\n+/g, '. ') // Replace newlines with periods
            .replace(/([.!?])\s*([.!?])+/g, '$1') // Remove duplicate punctuation
            .replace(/\b(https?:\/\/[^\s]+)/g, 'link') // Replace URLs with "link"
            .replace(/\b\d{4,}\b/g, (match) => { // Break up long numbers
                return match.split('').join(' ');
            })
            .trim();

        // Limit length for better performance
        if (cleanText.length > 3000) {
            cleanText = cleanText.substring(0, 3000) + '... text truncated for speech.';
        }

        return cleanText;
    }

    // Event handlers (can be overridden)
    onSpeechStart() {
        // Update UI to show speaking state
        document.querySelectorAll('.speak-btn, .speak-answer, .speak-question').forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-stop';
            }
            btn.classList.add('speaking');
        });
    }

    onSpeechEnd() {
        // Update UI to show stopped state
        document.querySelectorAll('.speak-btn, .speak-answer, .speak-question').forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-volume-up';
            }
            btn.classList.remove('speaking');
        });
    }

    onSpeechPause() {
        // Update UI to show paused state
        document.querySelectorAll('.speaking').forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-play';
            }
        });
    }

    onSpeechResume() {
        // Update UI to show resumed state
        document.querySelectorAll('.speaking').forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-stop';
            }
        });
    }

    onSpeechError(error) {
        console.error('Speech synthesis error:', error);
        
        // Show user-friendly error message
        if (window.AITutor && window.AITutor.NotificationManager) {
            window.AITutor.NotificationManager.show(
                'Speech playback failed. Please try again.',
                'warning',
                3000
            );
        }
    }

    // Get available voices for settings
    getVoices() {
        return this.voices;
    }

    // Update settings
    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
    }

    // Get current settings
    getSettings() {
        return { ...this.settings };
    }
}

// Initialize speech manager
const speechManager = new SpeechManager();

// Global function for easy access
function speakText(text, options = {}) {
    speechManager.speak(text, options);
}

function stopSpeech() {
    speechManager.stop();
}

function pauseSpeech() {
    speechManager.pause();
}

function resumeSpeech() {
    speechManager.resume();
}

// Auto-attach to speech buttons when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Handle speech buttons with text in data attribute
    document.addEventListener('click', function(e) {
        const target = e.target.closest('.speak-btn, .speak-answer, .speak-question, [data-speak]');
        if (!target) return;

        e.preventDefault();

        // If currently speaking, stop
        if (speechManager.isSpeaking()) {
            speechManager.stop();
            return;
        }

        // Get text to speak
        let textToSpeak = '';
        
        if (target.hasAttribute('data-text')) {
            textToSpeak = target.getAttribute('data-text');
        } else if (target.hasAttribute('data-speak')) {
            const selector = target.getAttribute('data-speak');
            const textElement = document.querySelector(selector);
            if (textElement) {
                textToSpeak = textElement.textContent || textElement.innerText;
            }
        } else {
            // Look for text in nearby elements
            const textContainer = target.closest('.modal-body, .card-body, .chat-bubble');
            if (textContainer) {
                const answerElement = textContainer.querySelector('#modal-answer, .chat-answer, [id*="answer"]');
                if (answerElement) {
                    textToSpeak = answerElement.textContent || answerElement.innerText;
                }
            }
        }

        if (textToSpeak) {
            speechManager.speak(textToSpeak);
        } else {
            console.warn('No text found to speak');
            if (window.AITutor && window.AITutor.NotificationManager) {
                window.AITutor.NotificationManager.show(
                    'No text available to read aloud.',
                    'warning',
                    2000
                );
            }
        }
    });

    // Handle keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Shift + S to toggle speech
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
            e.preventDefault();
            
            if (speechManager.isSpeaking()) {
                speechManager.stop();
            } else {
                // Try to speak selected text or current modal content
                const selection = window.getSelection().toString();
                if (selection) {
                    speechManager.speak(selection);
                } else {
                    const modal = document.querySelector('.modal.show');
                    if (modal) {
                        const modalAnswer = modal.querySelector('#modal-answer, .modal-body');
                        if (modalAnswer) {
                            speechManager.speak(modalAnswer.textContent);
                        }
                    }
                }
            }
        }
        
        // Escape to stop speech
        if (e.key === 'Escape' && speechManager.isSpeaking()) {
            speechManager.stop();
        }
    });

    // Add speech controls to appropriate elements
    function addSpeechControls() {
        // Add to chat answers
        document.querySelectorAll('.chat-answer, #modal-answer').forEach(element => {
            if (!element.querySelector('.speech-control')) {
                const speechBtn = document.createElement('button');
                speechBtn.className = 'btn btn-sm btn-outline-secondary speech-control ms-2';
                speechBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
                speechBtn.title = 'Read aloud (Ctrl+Shift+S)';
                speechBtn.setAttribute('data-text', element.textContent);
                
                // Insert after element or in a control container
                const container = element.parentNode.querySelector('.chat-controls') || element.parentNode;
                if (container) {
                    container.appendChild(speechBtn);
                }
            }
        });
    }

    // Initialize speech controls
    addSpeechControls();

    // Re-add speech controls when new content is loaded
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if new content has been added that might need speech controls
                const hasNewContent = Array.from(mutation.addedNodes).some(node => 
                    node.nodeType === Node.ELEMENT_NODE && 
                    (node.classList.contains('chat-answer') || 
                     node.querySelector && node.querySelector('.chat-answer, #modal-answer'))
                );
                
                if (hasNewContent) {
                    setTimeout(addSpeechControls, 100);
                }
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    console.log('Speech functionality initialized');
});

// Export for global use
window.speechManager = speechManager;
window.speakText = speakText;
window.stopSpeech = stopSpeech;
window.pauseSpeech = pauseSpeech;
window.resumeSpeech = resumeSpeech;

// Add CSS for speech button states
const speechStyles = document.createElement('style');
speechStyles.textContent = `
    .speaking {
        background-color: var(--danger-color) !important;
        border-color: var(--danger-color) !important;
        color: white !important;
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }

    .speech-control {
        transition: all 0.3s ease;
    }

    .speech-control:hover {
        transform: scale(1.1);
    }

    .speak-btn[disabled],
    .speak-answer[disabled],
    .speak-question[disabled] {
        opacity: 0.6;
        cursor: not-allowed;
    }
`;

document.head.appendChild(speechStyles);
