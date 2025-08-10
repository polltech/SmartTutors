import os
import logging
from datetime import datetime
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    print("Warning: google-genai package not found. Please install it.")

# Initialize Gemini client
def get_gemini_client():
    if not GOOGLE_GENAI_AVAILABLE:
        raise ImportError("Google Gemini package not available. Please install google-genai.")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Try to get from AdminSettings if available
        try:
            from models import AdminSettings
            settings = AdminSettings.get_settings()
            api_key = settings.gemini_api_key
        except:
            pass
    
    if not api_key:
        raise ValueError("Gemini API key not found in environment or admin settings")
    
    return genai.Client(api_key=api_key)

def get_ai_response(question, education_level, curriculum, subject=None, user_id=None):
    """
    Get AI response based on user's education level and curriculum
    """
    try:
        client = get_gemini_client()
        
        # Create age-appropriate system prompt with formatting
        system_prompt = f"""
        You are an expert AI tutor specializing in the {curriculum} curriculum for {education_level} students.
        
        Instructions:
        1. Respond in a way appropriate for {education_level} students
        2. Use simple, clear language that matches their comprehension level
        3. Provide step-by-step explanations when needed
        4. Be encouraging and supportive like a real teacher
        5. If this is about {subject}, focus on that subject area
        6. For math/science questions, show step-by-step solutions
        7. For exam questions, provide clear explanations for each answer
        8. Keep responses educational but engaging
        9. If asked about inappropriate content, redirect to educational topics
        10. Always be helpful, patient, and kind
        
        STRUCTURED RESPONSE FORMAT:
        You must format your response using this exact structure:
        
        ✅ **Answer:** [Provide the main answer here]
        
        📘 **Step-by-Step Explanation:**
        Step 1: [Clear explanation of first step]
        Step 2: [Clear explanation of second step]
        Step 3: [Continue as needed]
        
        🖼️ **Visual Aid:** [Describe any helpful diagram/image, or write "None needed"]
        
        🔊 **Summary:** [One paragraph summary for text-to-speech reading]
        
        Educational Level: {education_level}
        Curriculum: {curriculum}
        Subject Focus: {subject or 'General'}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user", 
                    parts=[types.Part(text=f"{system_prompt}\n\nStudent Question: {question}")]
                )
            ]
        )
        
        if response and response.text:
            return format_structured_response(response.text)
        else:
            return "I'm sorry, I couldn't generate a response at the moment. Please try again."
            
    except Exception as e:
        logging.error(f"Error getting AI response: {e}")
        return f"I'm experiencing some technical difficulties. Please try again later. Error: {str(e)}"

def format_structured_response(response_text):
    """
    Format AI response with proper HTML structure for educational display
    """
    try:
        # Check if response follows structured format
        if '✅ **Answer:**' not in response_text:
            # If not structured, return with basic formatting
            return format_basic_response(response_text)
        
        # Parse structured response
        sections = {}
        current_section = None
        current_content = []
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('✅ **Answer:**'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'answer'
                current_content = [line.replace('✅ **Answer:**', '').strip()]
            elif line.startswith('📘 **Step-by-Step Explanation:**'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'explanation'
                current_content = []
            elif line.startswith('🖼️ **Visual Aid:**'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'visual'
                current_content = [line.replace('🖼️ **Visual Aid:**', '').strip()]
            elif line.startswith('🔊 **Summary:**'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'summary'
                current_content = [line.replace('🔊 **Summary:**', '').strip()]
            elif line and current_section:
                current_content.append(line)
        
        # Add final section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        # Build structured HTML
        html_parts = ['<div class="structured-ai-response">']
        
        # Answer section
        if 'answer' in sections:
            html_parts.append(f'''
            <div class="answer-section">
                <div class="section-header">
                    <i class="fas fa-check-circle text-success"></i>
                    <strong>Answer</strong>
                </div>
                <div class="answer-content highlight-box">
                    {sections['answer']}
                </div>
            </div>
            ''')
        
        # Explanation section
        if 'explanation' in sections:
            formatted_steps = format_explanation_steps(sections['explanation'])
            html_parts.append(f'''
            <div class="explanation-section">
                <div class="section-header">
                    <i class="fas fa-book text-primary"></i>
                    <strong>Step-by-Step Explanation</strong>
                </div>
                <div class="explanation-content">
                    {formatted_steps}
                </div>
            </div>
            ''')
        
        # Visual aid section
        if 'visual' in sections and sections['visual'].lower() not in ['none needed', 'none', '']:
            html_parts.append(f'''
            <div class="visual-section">
                <div class="section-header">
                    <i class="fas fa-image text-info"></i>
                    <strong>Visual Aid</strong>
                </div>
                <div class="visual-content info-box">
                    <i class="fas fa-lightbulb"></i> {sections['visual']}
                </div>
            </div>
            ''')
        
        # Summary section with text-to-speech
        if 'summary' in sections:
            summary_text = sections['summary'].replace('"', "'").replace('\n', ' ').strip()
            html_parts.append(f'''
            <div class="summary-section">
                <div class="section-header">
                    <i class="fas fa-volume-up text-warning"></i>
                    <strong>Summary</strong>
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="speakText(this)" data-text="{summary_text}">
                        <i class="fas fa-play"></i> Listen
                    </button>
                </div>
                <div class="summary-content">
                    {sections['summary']}
                </div>
            </div>
            ''')
        
        html_parts.append('</div>')
        return ''.join(html_parts)
        
    except Exception as e:
        logging.error(f"Error formatting structured response: {e}")
        return format_basic_response(response_text)

def format_explanation_steps(explanation_text):
    """
    Format step-by-step explanations with proper styling
    """
    try:
        lines = explanation_text.split('\n')
        formatted_parts = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.lower().startswith('step '):
                # Extract step number and content
                parts = line.split(':', 1)
                if len(parts) == 2:
                    step_header = parts[0].strip()
                    step_content = parts[1].strip()
                    formatted_parts.append(f'''
                    <div class="step-item">
                        <div class="step-header">{step_header}</div>
                        <div class="step-content">{step_content}</div>
                    </div>
                    ''')
                else:
                    formatted_parts.append(f'<div class="step-item"><div class="step-content">{line}</div></div>')
            elif line.startswith(('a)', 'b)', 'c)', 'd)', 'A)', 'B)', 'C)', 'D)')):
                formatted_parts.append(f'<div class="letter-item"><strong>{line[:2]}</strong> {line[2:].strip()}</div>')
            elif line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                num_part = line.split('.', 1)
                if len(num_part) == 2:
                    formatted_parts.append(f'<div class="number-item"><strong>{num_part[0]}.</strong> {num_part[1].strip()}</div>')
                else:
                    formatted_parts.append(f'<div class="explanation-text">{line}</div>')
            elif line.startswith(('- ', '• ')):
                formatted_parts.append(f'<div class="bullet-item">• {line[2:].strip()}</div>')
            else:
                formatted_parts.append(f'<div class="explanation-text">{line}</div>')
        
        return ''.join(formatted_parts)
        
    except Exception as e:
        logging.error(f"Error formatting explanation steps: {e}")
        return explanation_text

def format_basic_response(response_text):
    """
    Format basic response when structured format is not used
    """
    try:
        # Apply basic formatting
        formatted = response_text
        formatted = formatted.replace('**', '<strong>').replace('**', '</strong>')
        formatted = formatted.replace('*', '<em>').replace('*', '</em>')
        
        # Handle line breaks
        paragraphs = formatted.split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            if paragraph.strip():
                if paragraph.strip().startswith('#'):
                    # Handle headers
                    level = len(paragraph.strip()) - len(paragraph.strip().lstrip('#'))
                    header_text = paragraph.strip()[level:].strip()
                    formatted_paragraphs.append(f'<h{min(level, 6)}>{header_text}</h{min(level, 6)}>')
                else:
                    formatted_paragraphs.append(f'<p>{paragraph.strip()}</p>')
        
        return f'<div class="basic-ai-response">{"".join(formatted_paragraphs)}</div>'
    except Exception as e:
        logging.error(f"Error formatting basic response: {e}")
        return f'<div class="basic-ai-response"><p>{response_text}</p></div>'

def generate_exam(topic, education_level, curriculum, subject=None, num_questions=10, question_type='mixed'):
    """
    Generate exam/quiz with questions and answers
    """
    try:
        client = get_gemini_client()
        
        # Build question type description
        type_descriptions = {
            'mcq': 'multiple choice questions with 4 options (A, B, C, D)',
            'short': 'short answer questions',
            'essay': 'essay questions requiring detailed responses',
            'mixed': 'a mix of multiple choice questions and short answer questions'
        }
        
        system_prompt = f"""
        You are creating an educational exam for {education_level} students following the {curriculum} curriculum.
        
        Topic: {topic}
        Subject: {subject or 'General'}
        Number of questions: {num_questions}
        Question type: {type_descriptions.get(question_type, 'mixed')}
        
        Create an exam with the following structure:
        
        🎯 **EXAM: {topic}**
        📚 **Level:** {education_level} • **Curriculum:** {curriculum}
        ⏰ **Time:** {num_questions * 2} minutes
        
        **INSTRUCTIONS:**
        - Read all questions carefully
        - Answer all questions
        - Show your working where applicable
        
        **QUESTIONS:**
        [Generate exactly {num_questions} questions appropriate for {education_level} level]
        
        **ANSWER KEY:**
        [Provide detailed answers with explanations for each question]
        
        **EXAM ANSWERS (TOGGLE SECTION):**
        <div class="exam-answers" style="display: none;">
        [Detailed answers and explanations here]
        </div>
        
        Make questions progressively challenging but appropriate for the education level.
        Include clear explanations for each answer to help students learn.
        """
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=system_prompt
        )
        
        if response.text:
            # Add toggle functionality for answers
            formatted_response = response.text
            formatted_response = add_exam_toggle_functionality(formatted_response)
            return formatted_response
        else:
            return "I couldn't generate the exam. Please try again with a different topic."
            
    except Exception as e:
        logging.error(f"Error generating exam: {e}")
        return f"I had trouble generating the exam. Error: {str(e)}"

def add_exam_toggle_functionality(exam_text):
    """
    Add JavaScript toggle functionality for exam answers
    """
    if "ANSWER KEY" in exam_text or "ANSWERS:" in exam_text:
        # Add toggle button and JavaScript
        toggle_html = """
        <div class="exam-controls mt-3 mb-3">
            <button class="btn btn-warning btn-sm" onclick="toggleExamAnswers()" id="toggle-answers-btn">
                <i class="fas fa-eye me-1"></i>Show Answers
            </button>
            <small class="text-muted ms-2">Click to reveal/hide answers</small>
        </div>
        
        <script>
        function toggleExamAnswers() {
            const answersSection = document.querySelector('.exam-answers');
            const toggleBtn = document.getElementById('toggle-answers-btn');
            
            if (answersSection.style.display === 'none') {
                answersSection.style.display = 'block';
                toggleBtn.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Answers';
                toggleBtn.className = 'btn btn-danger btn-sm';
            } else {
                answersSection.style.display = 'none';
                toggleBtn.innerHTML = '<i class="fas fa-eye me-1"></i>Show Answers';
                toggleBtn.className = 'btn btn-warning btn-sm';
            }
        }
        </script>
        """
        
        # Insert toggle controls before answers section
        exam_text = exam_text.replace("**ANSWER KEY:**", toggle_html + "**ANSWER KEY:**")
        exam_text = exam_text.replace("**ANSWERS:**", toggle_html + "**ANSWERS:**")
        
        # Wrap answers in toggleable div
        if "<div class=\"exam-answers\"" not in exam_text:
            # Find and wrap the answers section
            import re
            answer_pattern = r"(\*\*ANSWER[S]?\s*KEY?\*\*.*?)(?=\n\n|\Z)"
            exam_text = re.sub(answer_pattern, r'<div class="exam-answers" style="display: none;">\1</div>', exam_text, flags=re.DOTALL)
    
    return exam_text

def generate_combined_response(topic, education_level, curriculum, subject=None):
    """
    Generate explanation with visual elements combined
    """
    try:
        client = get_gemini_client()
        
        system_prompt = f"""
        You are creating a comprehensive educational resource for {education_level} students following the {curriculum} curriculum.
        
        Topic: {topic}
        Subject: {subject or 'General'}
        
        Create a complete educational package with:
        
        🌟 **COMPLETE LEARNING PACKAGE: {topic}**
        
        📖 **Introduction:**
        [Brief engaging introduction]
        
        ✅ **Detailed Explanation:**
        [Comprehensive explanation with clear language]
        
        📊 **Visual Elements:**
        [Describe helpful diagrams, charts, or illustrations]
        [Include simple SVG diagrams where applicable]
        
        💡 **Interactive Examples:**
        [Examples students can work through]
        
        🎯 **Practice Questions:**
        [2-3 questions to test understanding]
        
        🖼️ **Visual Learning Aids:**
        [SVG diagrams, charts, or visual descriptions]
        
        📚 **Summary:**
        [Key points to remember]
        
        Make this a complete learning experience appropriate for {education_level} level.
        Include visual elements that enhance understanding.
        """
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=system_prompt
        )
        
        if response.text:
            formatted_response = add_svg_rendering_support(response.text)
            return add_interactive_elements(formatted_response)
        else:
            return "I couldn't generate the combined response. Please try again."
            
    except Exception as e:
        logging.error(f"Error generating combined response: {e}")
        return f"I had trouble creating the learning package. Error: {str(e)}"

def add_svg_rendering_support(text):
    """
    Enhance text with SVG rendering capabilities
    """
    # Add CSS for SVG styling
    svg_css = """
    <style>
    .educational-svg {
        max-width: 100%;
        height: auto;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        background: #f8f9fa;
        margin: 15px 0;
    }
    .svg-container {
        text-align: center;
        margin: 20px 0;
    }
    .svg-description {
        margin-top: 10px;
        font-size: 0.9em;
        color: #666;
    }
    </style>
    """
    
    # Find SVG code and wrap it properly
    import re
    svg_pattern = r"(<svg[^>]*>.*?</svg>)"
    text = re.sub(svg_pattern, r'<div class="svg-container"><div class="educational-svg">\1</div></div>', text, flags=re.DOTALL)
    
    return svg_css + text

def add_interactive_elements(text):
    """
    Add interactive elements to enhance learning
    """
    interactive_css = """
    <style>
    .practice-question {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 15px;
        margin: 15px 0;
        border-radius: 5px;
    }
    .answer-reveal {
        background: #f1f8e9;
        border: 1px solid #8bc34a;
        border-radius: 5px;
        padding: 10px;
        margin-top: 10px;
        display: none;
    }
    .reveal-btn {
        margin-top: 10px;
    }
    </style>
    """
    
    # Find practice questions and make them interactive
    import re
    
    # Wrap practice questions in interactive divs
    question_pattern = r"(🎯\s*\*\*Practice\s*Questions?\*\*.*?)(?=\n\n|🖼️|\Z)"
    text = re.sub(question_pattern, r'<div class="practice-section">\1</div>', text, flags=re.DOTALL)
    
    return interactive_css + text

def update_api_keys_from_admin(hf_token=None, pixabay_key=None, unsplash_key=None, pexels_key=None, gemini_key=None):
    """
    Update API keys from admin panel settings
    """
    try:
        from models import AdminSettings
        settings = AdminSettings.get_settings()
        
        if hf_token:
            settings.hf_token = hf_token
        if pixabay_key:
            settings.pixabay_key = pixabay_key
        if unsplash_key:
            settings.unsplash_key = unsplash_key
        if pexels_key:
            settings.pexels_key = pexels_key
        if gemini_key:
            settings.gemini_api_key = gemini_key
            
        # Commit changes to database
        from app import db
        db.session.commit()
        
        return True
    except Exception as e:
        logging.error(f"Error updating API keys: {e}")
        return False

def get_current_api_keys():
    """
    Get current API keys for display/testing
    """
    try:
        from models import AdminSettings
        settings = AdminSettings.get_settings()
        return {
            'hf_token': settings.hf_token,
            'pixabay_key': settings.pixabay_key,
            'unsplash_key': settings.unsplash_key,
            'pexels_key': settings.pexels_key,
            'gemini_key': settings.gemini_api_key
        }
    except Exception as e:
        logging.error(f"Error getting API keys: {e}")
        return {}

# Initialize API keys from environment
def initialize_api_keys(settings=None):
    """
    Initialize API keys from environment or admin settings
    """
    pass  # This will be handled by the update_api_keys_from_admin function
