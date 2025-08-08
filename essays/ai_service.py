"""
AI service for Django Essay Coach Application
Contains all AI-related functions for essay analysis and feedback generation
"""
import openai
from openai import OpenAI
import json
import time
import logging
import re
import datetime
from django.conf import settings
from .models import EssayAnalysis, ChecklistProgress

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def normalize_essay_type(essay_type):
    """
    Normalize essay type to standard values
    
    Args:
        essay_type (str): Raw essay type input
    
    Returns:
        str: Normalized essay type
    """
    if not essay_type:
        return 'argumentative'
    
    essay_type_lower = essay_type.lower().strip()
    
    # Map variations to standard types
    if any(word in essay_type_lower for word in ['argument', 'persuasive', 'opinion', 'convince']):
        return 'argumentative'
    elif any(word in essay_type_lower for word in ['narrative', 'story', 'personal', 'experience']):
        return 'narrative'
    elif any(word in essay_type_lower for word in ['expository', 'explain', 'informative', 'inform']):
        return 'expository'
    elif any(word in essay_type_lower for word in ['descriptive', 'describe', 'detail']):
        return 'descriptive'
    elif any(word in essay_type_lower for word in ['compare', 'contrast', 'comparison']):
        return 'compare_contrast'
    elif any(word in essay_type_lower for word in ['cause', 'effect', 'reason', 'result']):
        return 'cause_effect'
    elif any(word in essay_type_lower for word in ['process', 'procedure', 'how to', 'step']):
        return 'process'
    elif any(word in essay_type_lower for word in ['definition', 'define', 'meaning']):
        return 'definition'
    elif any(word in essay_type_lower for word in ['classification', 'classify', 'category']):
        return 'classification'
    else:
        return 'argumentative'


def analyze_essay_with_ai(essay_text, essay_type, max_retries=3, retry_delay=2):
    """
    Analyze essay using OpenAI API with comprehensive error handling and retry logic
    
    Args:
        essay_text (str): The essay text to analyze
        essay_type (str): Type of essay (argumentative, narrative, etc.)
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retry attempts in seconds
    
    Returns:
        dict: Analysis results with scores and feedback
    """
    normalized_type = normalize_essay_type(essay_type)
    
    # Essay type specific prompts
    type_prompts = {
        'argumentative': """
        This is an argumentative essay. Focus your analysis on:
        - Thesis clarity and argumentation strength
        - Use of evidence and examples
        - Counter-argument acknowledgment
        - Logical flow and persuasive techniques
        - Conclusion effectiveness
        """,
        'narrative': """
        This is a narrative essay. Focus your analysis on:
        - Story structure and plot development
        - Character development and dialogue
        - Setting and atmosphere
        - Use of narrative techniques
        - Theme and meaning
        """,
        'expository': """
        This is an expository essay. Focus your analysis on:
        - Clarity of explanation
        - Organization of information
        - Use of examples and details
        - Transition between ideas
        - Factual accuracy and objectivity
        """,
        'descriptive': """
        This is a descriptive essay. Focus your analysis on:
        - Vivid imagery and sensory details
        - Organization of description
        - Use of figurative language
        - Mood and atmosphere creation
        - Overall impression and coherence
        """
    }
    
    specific_prompt = type_prompts.get(normalized_type, type_prompts['argumentative'])
    
    prompt = f"""
    You are an expert essay evaluator and writing instructor. Analyze the following {normalized_type} essay and provide comprehensive feedback.

    {specific_prompt}

    Essay to analyze:
    \"\"\"{essay_text}\"\"\"

    Please provide your analysis in the following JSON format:
    {{
        "overall_score": [score out of 100],
        "grammar_score": [score out of 30],
        "clarity_score": [score out of 25],
        "structure_score": [score out of 25],
        "content_score": [score out of 20],
        "tagged_essay": "[essay text with inline correction tags like <delete>word</delete>, <add>word</add>, <replace>old|new</replace>]",
        "detailed_feedback": {{
            "grammar": "[detailed grammar feedback]",
            "clarity": "[detailed clarity feedback]",
            "structure": "[detailed structure feedback]",
            "content": "[detailed content feedback]"
        }},
        "suggestions": [
            {{"type": "delete", "text": "word", "reason": "brief grammatical reason (e.g., 'redundant', 'unclear pronoun', 'word repetition')"}},
            {{"type": "add", "text": "word", "reason": "brief grammatical reason (e.g., 'missing article', 'needs transition', 'subject-verb agreement')"}},
            {{"type": "replace", "text": "old|new", "reason": "brief grammatical reason (e.g., 'wrong tense', 'better word choice', 'passive to active voice')"}}
        ],
        "scores": {{
            "ideas": [content_score],
            "organization": [structure_score], 
            "style": [clarity_score],
            "grammar": [grammar_score]
        }},
        "score_reasons": {{
            "ideas": "[detailed explanation of content score]",
            "organization": "[detailed explanation of structure score]",
            "style": "[detailed explanation of style score]", 
            "grammar": "[detailed explanation of grammar score]"
        }},
        "strengths": [
            "[strength 1]",
            "[strength 2]",
            "[strength 3]"
        ],
        "areas_improvement": [
            "[area for improvement 1]",
            "[area for improvement 2]",
            "[area for improvement 3]"
        ]
    }}

    IMPORTANT: In the tagged_essay field, use these tags to mark ONLY INDIVIDUAL WORDS (never phrases or sentences):
    - <delete>word</delete> for single words that should be removed (ONE word only)
    - <add>word</add> for single words that should be added (ONE word only)  
    - <replace>old_word|new_word</replace> for single word substitutions (ONE word to ONE word)
    
    CRITICAL: Each tag must contain exactly ONE word. Never tag multiple words together like <delete>very good</delete>. 
    Instead use: <delete>very</delete> <delete>good</delete>
    
    For suggestions, provide CONCISE grammatical explanations (2-4 words max):
    - Grammar errors: "wrong tense", "subject-verb agreement", "missing article"
    - Style issues: "redundant", "unclear pronoun", "word repetition" 
    - Clarity: "better word choice", "passive to active", "needs transition"
    
    Example of correct word-by-word tagging:
    "I am <delete>very</delete> <delete>much</delete> excited <add>about</add> this <replace>opportunity|chance</replace>."
    
    Ensure all scores are realistic numbers between 0-100, and provide constructive, specific feedback with actionable word-level suggestions.
    """
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting AI analysis (attempt {attempt + 1}/{max_retries})")
            
            # Check if API key is available
            if not settings.OPENAI_API_KEY:
                logger.error("OpenAI API key not configured")
                return get_fallback_analysis(essay_text, normalized_type)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert essay evaluator and writing instructor."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,  # Increased from 2000 to handle longer tagged essays
                temperature=0.7
            )
            
            # Extract and parse the response
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"AI response received: {len(ai_response)} characters")
            
            if not ai_response:
                logger.warning("Empty AI response received")
                if attempt == max_retries - 1:
                    return get_fallback_analysis(essay_text, normalized_type)
                continue
            
            logger.info("AI analysis completed successfully")
            
            # Parse JSON response
            try:
                # Clean the response - remove markdown code blocks if present
                clean_response = ai_response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]  # Remove ```json
                if clean_response.startswith('```'):
                    clean_response = clean_response[3:]   # Remove ```
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]  # Remove trailing ```
                
                clean_response = clean_response.strip()
                
                analysis_result = json.loads(clean_response)
                
                # Validate required fields
                required_fields = ['overall_score', 'grammar_score', 'clarity_score', 'structure_score', 'content_score']
                for field in required_fields:
                    if field not in analysis_result:
                        raise ValueError(f"Missing required field: {field}")
                
                # Ensure scores are within valid range
                for field in required_fields:
                    score = analysis_result[field]
                    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                        analysis_result[field] = 50  # Default fallback score
                
                # Ensure new fields exist with defaults
                if 'tagged_essay' not in analysis_result:
                    analysis_result['tagged_essay'] = essay_text
                
                if 'scores' not in analysis_result:
                    analysis_result['scores'] = {
                        'ideas': analysis_result.get('content_score', 75),
                        'organization': analysis_result.get('structure_score', 75),
                        'style': analysis_result.get('clarity_score', 75),
                        'grammar': analysis_result.get('grammar_score', 75)
                    }
                
                if 'score_reasons' not in analysis_result:
                    analysis_result['score_reasons'] = {
                        'ideas': analysis_result.get('detailed_feedback', {}).get('content', 'Content analysis completed.'),
                        'organization': analysis_result.get('detailed_feedback', {}).get('structure', 'Structure analysis completed.'),
                        'style': analysis_result.get('detailed_feedback', {}).get('clarity', 'Style analysis completed.'),
                        'grammar': analysis_result.get('detailed_feedback', {}).get('grammar', 'Grammar analysis completed.')
                    }
                
                # Ensure suggestions is properly formatted
                if 'suggestions' not in analysis_result:
                    analysis_result['suggestions'] = []
                elif isinstance(analysis_result['suggestions'], list):
                    # Convert string suggestions to structured format if needed
                    formatted_suggestions = []
                    for suggestion in analysis_result['suggestions']:
                        if isinstance(suggestion, str):
                            formatted_suggestions.append({
                                'type': 'general',
                                'text': suggestion,
                                'reason': suggestion
                            })
                        else:
                            formatted_suggestions.append(suggestion)
                    analysis_result['suggestions'] = formatted_suggestions
                
                logger.info("AI analysis parsed and validated successfully")
                return analysis_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Raw AI response: {ai_response[:1000]}...")  # Log first 1000 chars
                logger.error(f"Cleaned response: {clean_response[:1000]}...")  # Log cleaned version
                
                # Try to extract partial data if possible
                try:
                    # Look for score patterns in the response
                    import re
                    scores = {}
                    score_patterns = [
                        (r'"overall_score":\s*(\d+)', 'overall_score'),
                        (r'"grammar_score":\s*(\d+)', 'grammar_score'),
                        (r'"clarity_score":\s*(\d+)', 'clarity_score'),
                        (r'"structure_score":\s*(\d+)', 'structure_score'),
                        (r'"content_score":\s*(\d+)', 'content_score')
                    ]
                    
                    for pattern, key in score_patterns:
                        match = re.search(pattern, ai_response)
                        if match:
                            scores[key] = int(match.group(1))
                    
                    # If we got some scores, create a partial result
                    if len(scores) >= 3:  # At least 3 scores found
                        logger.info("Creating partial analysis from extracted scores")
                        partial_result = get_fallback_analysis(essay_text, normalized_type)
                        partial_result.update(scores)
                        return partial_result
                except Exception as parse_error:
                    logger.error(f"Failed to extract partial data: {parse_error}")
                
                if attempt == max_retries - 1:
                    return get_fallback_analysis(essay_text, normalized_type)
                
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit reached (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                return get_fallback_analysis(essay_text, normalized_type)
        
        except Exception as e:
            logger.error(f"Unexpected error during AI analysis (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return get_fallback_analysis(essay_text, normalized_type)
            
        time.sleep(retry_delay)  # Wait before retry
                
    # If all retries failed, return fallback analysis
    return get_fallback_analysis(essay_text, normalized_type)


def get_fallback_analysis(essay_text, essay_type):
    """
    Generate fallback analysis when AI analysis fails
    
    Args:
        essay_text (str): The essay text
        essay_type (str): Type of essay
    
    Returns:
        dict: Basic analysis results
    """
    word_count = len(essay_text.split())
    sentence_count = len([s for s in re.split(r'[.!?]+', essay_text) if s.strip()])
    
    # Basic scoring based on text metrics
    if word_count < 100:
        base_score = 40
    elif word_count < 300:
        base_score = 60
    elif word_count < 500:
        base_score = 75
    else:
        base_score = 85
    
    return {
        "overall_score": base_score,
        "grammar_score": base_score - 5,
        "clarity_score": base_score,
        "structure_score": base_score + 5,
        "content_score": base_score,
        "tagged_essay": essay_text,  # No markup for fallback
        "scores": {
            "ideas": base_score,
            "organization": base_score + 5,
            "style": base_score,
            "grammar": base_score - 5
        },
        "score_reasons": {
            "ideas": f"Content analysis shows {word_count} words with basic {essay_type} structure.",
            "organization": f"Essay organization appears adequate with {sentence_count} sentences.",
            "style": "Writing style is developing but needs more refinement.",
            "grammar": "Grammar analysis unavailable due to AI service limitations."
        },
        "detailed_feedback": {
            "grammar": "Basic grammar analysis unavailable due to AI service limitations.",
            "clarity": f"Your essay contains {word_count} words and {sentence_count} sentences.",
            "structure": "Please review essay structure and organization.",
            "content": f"Continue developing your {essay_type} essay with more detailed content."
        },
        "suggestions": [
            {"type": "general", "text": "Review grammar and spelling carefully", "reason": "Improve overall writing quality"},
            {"type": "general", "text": "Enhance content with more specific examples", "reason": "Strengthen your arguments with evidence"},
            {"type": "general", "text": "Improve essay structure and flow", "reason": "Better organization improves readability"}
        ],
        "strengths": [
            f"Essay meets basic {essay_type} requirements",
            "Appropriate length for the assignment",
            "Clear topic focus"
        ],
        "areas_improvement": [
            "Grammar and language use",
            "Content development",
            "Essay organization"
        ]
    }


def generate_step_wise_checklist(analysis_result, essay_type):
    """
    Generate a step-by-step improvement checklist based on analysis results
    
    Args:
        analysis_result (dict): Results from essay analysis
        essay_type (str): Type of essay
    
    Returns:
        dict: Structured checklist for improvement
    """
    checklist = {
        "essay_type": essay_type,
        "generated_at": datetime.datetime.now().isoformat(),
        "total_steps": 0,
        "categories": {}
    }
    
    # Grammar improvements
    if analysis_result.get('grammar_score', 0) < 70:
        checklist["categories"]["Grammar"] = {
            "priority": "high",
            "steps": [
                "Review sentence structure and fix run-on sentences",
                "Check subject-verb agreement throughout the essay",
                "Correct punctuation errors, especially commas and periods",
                "Fix spelling mistakes and typos",
                "Ensure proper capitalization"
            ]
        }
    
    # Clarity improvements
    if analysis_result.get('clarity_score', 0) < 70:
        checklist["categories"]["Clarity"] = {
            "priority": "medium",
            "steps": [
                "Simplify complex sentences for better readability",
                "Replace vague words with specific, concrete terms",
                "Eliminate unnecessary repetition",
                "Use active voice instead of passive voice where appropriate",
                "Ensure each paragraph has a clear main idea"
            ]
        }
    
    # Structure improvements
    if analysis_result.get('structure_score', 0) < 70:
        checklist["categories"]["Structure"] = {
            "priority": "high",
            "steps": [
                "Create a clear introduction with thesis statement",
                "Organize body paragraphs with topic sentences",
                "Improve transitions between paragraphs",
                "Develop a strong conclusion that reinforces main points",
                "Check overall essay organization and flow"
            ]
        }
    
    # Content improvements
    if analysis_result.get('content_score', 0) < 70:
        checklist["categories"]["Content"] = {
            "priority": "medium",
            "steps": [
                "Add more specific examples and evidence",
                "Develop ideas more thoroughly",
                "Ensure content is relevant to the essay topic",
                "Include more detailed analysis and explanation",
                "Strengthen arguments with supporting details"
            ]
        }
    
    # Count total steps
    total_steps = sum(len(category["steps"]) for category in checklist["categories"].values())
    checklist["total_steps"] = total_steps
    
    return checklist


def save_analysis_to_database(student, essay_text, essay_type, analysis_result):
    """
    Save analysis results to the database
    
    Args:
        student: User model instance
        essay_text (str): The essay text
        essay_type (str): Type of essay
        analysis_result (dict): Analysis results from AI
    
    Returns:
        EssayAnalysis: Created analysis instance
    """
    try:
        # Prepare detailed_feedback to include all the analysis data
        detailed_feedback = analysis_result.get('detailed_feedback', {})
        
        # Add the new structured data to detailed_feedback
        if 'tagged_essay' in analysis_result:
            detailed_feedback['tagged_essay'] = analysis_result['tagged_essay']
        if 'scores' in analysis_result:
            detailed_feedback['scores'] = analysis_result['scores']
        if 'score_reasons' in analysis_result:
            detailed_feedback['score_reasons'] = analysis_result['score_reasons']
        
        analysis = EssayAnalysis.objects.create(
            student=student,
            essay_text=essay_text,
            essay_type=normalize_essay_type(essay_type),
            overall_score=analysis_result.get('overall_score', 0),
            grammar_score=analysis_result.get('grammar_score', 0),
            clarity_score=analysis_result.get('clarity_score', 0),
            structure_score=analysis_result.get('structure_score', 0),
            content_score=analysis_result.get('content_score', 0),
            detailed_feedback=detailed_feedback,
            suggestions=analysis_result.get('suggestions', []),
            strengths=analysis_result.get('strengths', []),
            areas_improvement=analysis_result.get('areas_improvement', [])
        )
        
        logger.info(f"Analysis saved to database with ID: {analysis.id}")
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to save analysis to database: {e}")
        raise


def save_checklist_progress(student, analysis, checklist_data):
    """
    Save checklist progress to the database
    
    Args:
        student: User model instance
        analysis: EssayAnalysis instance
        checklist_data (dict): Checklist data
    
    Returns:
        ChecklistProgress: Created or updated progress instance
    """
    try:
        progress, created = ChecklistProgress.objects.get_or_create(
            student=student,
            analysis=analysis,
            defaults={
                'checklist_data': checklist_data,
                'completed_items': [],
                'progress_percentage': 0.0
            }
        )
        
        if not created:
            progress.checklist_data = checklist_data
            progress.save()
        
        logger.info(f"Checklist progress saved for student: {student.username}")
        return progress
        
    except Exception as e:
        logger.error(f"Failed to save checklist progress: {e}")
        raise
