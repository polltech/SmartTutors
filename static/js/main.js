// Main JavaScript file for AI Smart Tutor

// Theme management
class ThemeManager {
    constructor() {
        this.currentTheme = 'blue';
        this.loadTheme();
    }

    loadTheme() {
        fetch('/api/theme')
            .then(response => response.json())
            .then(data => {
                this.applyTheme(data);
            })
            .catch(error => {
                console.log('Failed to load theme:', error);
            });
    }

    applyTheme(themeData) {
        this.currentTheme = themeData.theme;
        document.body.setAttribute('data-theme', this.currentTheme);
        
        // Apply background
        this.setBackground(themeData);
    }

    setBackground(themeData) {
        const backgroundContainer = document.getElementById('background-container');
        if (!backgroundContainer) return;

        if (themeData.background_url) {
            if (themeData.background_type === 'video') {
                backgroundContainer.innerHTML = `
                    <video autoplay loop ${themeData.video_muted ? 'muted' : ''} class="background-video">
                        <source src="${themeData.background_url}" type="video/mp4">
                    </video>
                    <div id="background-overlay"></div>
                `;
            } else {
                backgroundContainer.style.backgroundImage = `url(${themeData.background_url})`;
                backgroundContainer.style.backgroundSize = 'cover';
                backgroundContainer.style.backgroundPosition = 'center';
                backgroundContainer.innerHTML = '<div id="background-overlay"></div>';
            }
        }
    }
}

// Animation utilities
class AnimationUtils {
    static fadeIn(element, duration = 500) {
        element.style.opacity = '0';
        element.style.display = 'block';
        
        const start = performance.now();
        
        function animate(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            element.style.opacity = progress;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }
        
        requestAnimationFrame(animate);
    }

    static slideIn(element, direction = 'left', duration = 500) {
        const startPos = direction === 'left' ? '-100%' : '100%';
        
        element.style.transform = `translateX(${startPos})`;
        element.style.display = 'block';
        
        const start = performance.now();
        
        function animate(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const currentPos = parseFloat(startPos) * (1 - easeOut);
            
            element.style.transform = `translateX(${currentPos}%)`;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }
        
        requestAnimationFrame(animate);
    }

    static bounce(element) {
        element.style.animation = 'bounce 0.6s ease-in-out';
        
        setTimeout(() => {
            element.style.animation = '';
        }, 600);
    }
}

// Notification system
class NotificationManager {
    static show(message, type = 'info', duration = 4000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        `;
        
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${this.getIcon(type)} me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }

    static getIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
}

// Form enhancement utilities
class FormUtils {
    static addLoadingState(button, loadingText = 'Loading...') {
        const originalText = button.innerHTML;
        button.innerHTML = `<span class="loading me-2"></span>${loadingText}`;
        button.disabled = true;
        
        return () => {
            button.innerHTML = originalText;
            button.disabled = false;
        };
    }

    static validateField(field, rules) {
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        if (rules.required && !value) {
            isValid = false;
            message = 'This field is required';
        } else if (rules.minLength && value.length < rules.minLength) {
            isValid = false;
            message = `Minimum ${rules.minLength} characters required`;
        } else if (rules.maxLength && value.length > rules.maxLength) {
            isValid = false;
            message = `Maximum ${rules.maxLength} characters allowed`;
        } else if (rules.email && !this.isValidEmail(value)) {
            isValid = false;
            message = 'Please enter a valid email address';
        }

        this.showFieldValidation(field, isValid, message);
        return isValid;
    }

    static isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    static showFieldValidation(field, isValid, message) {
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            if (feedback) {
                feedback.textContent = message;
            }
        }
    }
}

// Copy to clipboard utility
class ClipboardUtils {
    static async copyText(text) {
        try {
            await navigator.clipboard.writeText(text);
            NotificationManager.show('Text copied to clipboard!', 'success', 2000);
            return true;
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            NotificationManager.show('Text copied to clipboard!', 'success', 2000);
            return true;
        }
    }

    static addCopyButtons() {
        // Add copy buttons to code blocks and important text
        const codeBlocks = document.querySelectorAll('pre, code');
        codeBlocks.forEach(block => {
            if (block.textContent.length > 20) {
                const copyBtn = document.createElement('button');
                copyBtn.className = 'btn btn-sm btn-outline-secondary copy-btn';
                copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                copyBtn.style.cssText = 'position: absolute; top: 5px; right: 5px; z-index: 10;';
                
                block.style.position = 'relative';
                block.appendChild(copyBtn);
                
                copyBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.copyText(block.textContent);
                });
            }
        });
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme manager
    const themeManager = new ThemeManager();
    
    // Add smooth scrolling to all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add copy buttons to appropriate elements
    ClipboardUtils.addCopyButtons();

    // Enhanced form submission with loading states
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                FormUtils.addLoadingState(submitBtn);
            }
        });
    });

    // Add hover effects to cards
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-100%)';
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
    });

    // Add loading overlay for page transitions
    document.querySelectorAll('a:not([href^="#"]):not([data-bs-toggle])').forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.href && !this.href.includes('javascript:') && !this.target) {
                // Show loading overlay
                const overlay = document.createElement('div');
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                `;
                overlay.innerHTML = '<div class="loading" style="width: 50px; height: 50px; border-width: 5px;"></div>';
                document.body.appendChild(overlay);
            }
        });
    });

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K to focus search (if exists)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[type="search"], input[name="question"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });

    // Add progress indicator for forms
    document.querySelectorAll('form[method="POST"]').forEach(form => {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        if (inputs.length > 0) {
            const progressBar = document.createElement('div');
            progressBar.className = 'progress mb-3';
            progressBar.style.height = '3px';
            progressBar.innerHTML = '<div class="progress-bar" role="progressbar"></div>';
            
            form.insertBefore(progressBar, form.firstChild);
            
            function updateProgress() {
                const filledInputs = Array.from(inputs).filter(input => input.value.trim() !== '');
                const progress = (filledInputs.length / inputs.length) * 100;
                progressBar.querySelector('.progress-bar').style.width = progress + '%';
            }
            
            inputs.forEach(input => {
                input.addEventListener('input', updateProgress);
                input.addEventListener('change', updateProgress);
            });
            
            updateProgress();
        }
    });

    console.log('AI Smart Tutor initialized successfully!');
});

// Global functions for use in templates
window.AITutor = {
    ThemeManager,
    AnimationUtils,
    NotificationManager,
    FormUtils,
    ClipboardUtils
};
